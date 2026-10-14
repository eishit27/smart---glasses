import asyncio
import logging
from typing import AsyncGenerator
from aiohttp import web, WSMsgType

logger = logging.getLogger(__name__)

class WiFiReceiver:
    """Receives JPEG frames over HTTP POST or WebSocket."""
    
    def __init__(self, host: str = "0.0.0.0", port: int = 8080):
        self.host = host
        self.port = port
        self.frame_queue: asyncio.Queue[bytes] = asyncio.Queue()
        self.app = web.Application()
        self.app.router.add_post('/frame', self.handle_post)
        self.app.router.add_get('/ws', self.handle_ws)
        self.runner = None

    def _authenticate_request(self, request: web.Request) -> bool:
        """Verifies Authorization header against the device pairing token."""
        auth_header = request.headers.get("Authorization", "")
        if not auth_header.startswith("Bearer "):
            # Also allow X-Auth-Token header
            token = request.headers.get("X-VisionAid-Token", "")
        else:
            token = auth_header.split(" ", 1)[1].strip()

        from security.crypto import SecurityManager
        sec_mgr = SecurityManager()
        return sec_mgr.verify_token(token)

    async def handle_post(self, request: web.Request) -> web.Response:
        """Handle incoming frame via HTTP POST with security verification."""
        if not self._authenticate_request(request):
            logger.warning(f"Unauthorized WiFi POST attempt rejected from {request.remote}")
            return web.Response(status=401, text="Unauthorized: Invalid or missing pairing token")

        try:
            data = await request.read()
            if not data:
                return web.Response(status=400, text="Empty payload")
            
            # Anti-DoS: Check maximum frame size (e.g. 5MB)
            if len(data) > 5 * 1024 * 1024:
                return web.Response(status=413, text="Payload too large")

            await self.frame_queue.put(data)
            return web.Response(status=200, text="OK")
        except Exception as e:
            logger.error(f"Error handling POST: {e}")
            return web.Response(status=500, text=str(e))

    async def handle_ws(self, request: web.Request) -> web.WebSocketResponse:
        """Handle incoming frames via WebSocket with security verification."""
        if not self._authenticate_request(request):
            logger.warning(f"Unauthorized WebSocket connection rejected from {request.remote}")
            return web.Response(status=401, text="Unauthorized: Invalid pairing token")

        ws = web.WebSocketResponse()
        await ws.prepare(request)
        
        logger.info(f"Authenticated WebSocket connection opened from {request.remote}")
        try:
            async for msg in ws:
                if msg.type == WSMsgType.BINARY:
                    if len(msg.data) <= 5 * 1024 * 1024:
                        await self.frame_queue.put(msg.data)
                    else:
                        logger.warning("Dropped oversized WebSocket frame")
                elif msg.type == WSMsgType.ERROR:
                    logger.error(f"WebSocket connection closed with exception {ws.exception()}")
        finally:
            logger.info("WebSocket connection closed.")
            
        return ws

    async def start_server(self):
        """Start the aiohttp server."""
        self.runner = web.AppRunner(self.app)
        await self.runner.setup()
        site = web.TCPSite(self.runner, self.host, self.port)
        logger.info(f"Starting WiFi receiver on {self.host}:{self.port}")
        await site.start()
        
        # Keep server running in background
        while True:
            await asyncio.sleep(3600)

    async def stop_server(self):
        """Stop the aiohttp server."""
        if self.runner:
            await self.runner.cleanup()

    async def receive_frames(self) -> AsyncGenerator[bytes, None]:
        """Generator that yields completed frames."""
        while True:
            frame = await self.frame_queue.get()
            yield frame
