import asyncio
import logging
from typing import AsyncGenerator, Optional
from bleak import BleakClient, BleakScanner
from config import BLEConfig

logger = logging.getLogger(__name__)

class BLEReceiver:
    """Receives JPEG frames over BLE using bleak."""
    
    def __init__(self, config: BLEConfig):
        self.config = config
        self.client: Optional[BleakClient] = None
        self.frame_queue: asyncio.Queue[bytes] = asyncio.Queue()
        self.current_frame = bytearray()
        self.connected = False

    def _notification_handler(self, sender: int, data: bytearray):
        """Handles incoming BLE notifications containing frame chunks."""
        self.current_frame.extend(data)
        
        # Check for JPEG EOF marker (FFD9)
        if len(self.current_frame) >= 2 and self.current_frame[-2:] == b'\xff\xd9':
            # Complete frame received
            frame_data = bytes(self.current_frame)
            try:
                self.frame_queue.put_nowait(frame_data)
            except asyncio.QueueFull:
                logger.warning("Frame queue full, dropping frame.")
            self.current_frame = bytearray()

    async def connect_and_run(self):
        """Connects to the BLE device and manages auto-reconnection."""
        while True:
            try:
                logger.info("Scanning for VisionAid glasses...")
                device = await BleakScanner.find_device_by_filter(
                    lambda d, ad: self.config.service_uuid.lower() in [u.lower() for u in ad.service_uuids]
                )
                
                if not device:
                    logger.warning("Device not found. Retrying in 5 seconds...")
                    await asyncio.sleep(5)
                    continue

                logger.info(f"Found device: {device.name} - {device.address}")
                
                async with BleakClient(device, disconnected_callback=self._handle_disconnect) as client:
                    self.client = client
                    self.connected = True
                    logger.info("Connected to VisionAid glasses.")
                    
                    # Security handshake: authenticate with pre-shared pairing token
                    from security.crypto import SecurityManager
                    sec_mgr = SecurityManager()
                    auth_payload = f"AUTH:{sec_mgr.pairing_token.decode('utf-8')}".encode('utf-8')
                    
                    try:
                        logger.info("Sending BLE security authentication handshake...")
                        await client.write_gatt_char(self.config.tx_char_uuid, auth_payload, response=True)
                        logger.info("BLE Security authentication handshake completed.")
                    except Exception as e:
                        logger.warning(f"Could not complete explicit auth write ({e}), proceeding with notifications.")

                    await client.start_notify(self.config.rx_char_uuid, self._notification_handler)
                    
                    # Keep connection alive while connected
                    while self.connected:
                        await asyncio.sleep(1)
                        
            except Exception as e:
                logger.error(f"BLE connection error: {e}")
                self.connected = False
                await asyncio.sleep(5)

    def _handle_disconnect(self, client: BleakClient):
        """Callback for when BLE connection drops."""
        logger.warning(f"Disconnected from {client.address}")
        self.connected = False
        self.client = None

    async def receive_frames(self) -> AsyncGenerator[bytes, None]:
        """Generator that yields completed frames."""
        while True:
            frame = await self.frame_queue.get()
            yield frame
