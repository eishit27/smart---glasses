#include "ble_comm.h"
#include <Arduino.h>
#include <BLEDevice.h>
#include <BLEServer.h>
#include <BLEUtils.h>
#include <BLE2902.h>
#include <BLESecurity.h>

#define SERVICE_UUID           "4fafc201-1fb5-459e-8fcc-c5c9c331914b"
#define CHARACTERISTIC_FRAME   "beb5483e-36e1-4688-b7f5-ea07361b26a8"
#define CHARACTERISTIC_CMD     "beb5483f-36e1-4688-b7f5-ea07361b26a8"

// Pre-shared security token hash (or salt) between glasses and companion device
// In production, this can be flashed via serial provisioning or NFC tap
static const char* EXPECTED_PAIRING_TOKEN = "visionaid-secure-pair-token";

static BLEServer* pServer = nullptr;
static BLECharacteristic* pFrameChar = nullptr;
static BLECharacteristic* pCmdChar = nullptr;

static bool deviceConnected = false;
static bool clientAuthenticated = false;
static unsigned long connectTimestamp = 0;
static const unsigned long AUTH_TIMEOUT_MS = 10000; // 10s to authenticate before kick

class MySecurityCallbacks : public BLESecurityCallbacks {
    uint32_t onPassKeyRequest() {
        Serial.println("BLE Passkey requested: 123456");
        return 123456;
    }
    void onPassKeyNotify(uint32_t pass_key) {
        Serial.printf("BLE On passkey Notify: %d\n", pass_key);
    }
    bool onConfirmPIN(uint32_t pass_key) {
        Serial.printf("BLE Confirm PIN: %d\n", pass_key);
        return true;
    }
    bool onSecurityRequest() {
        return true;
    }
    void onAuthenticationComplete(esp_ble_auth_cmpl_t cmpl) {
        if (cmpl.success) {
            Serial.println("BLE Secure Pairing Success!");
        } else {
            Serial.printf("BLE Secure Pairing Failed: error 0x%x\n", cmpl.fail_reason);
        }
    }
};

class CommandCallbacks: public BLECharacteristicCallbacks {
    void onWrite(BLECharacteristic *pCharacteristic) {
        std::string value = pCharacteristic->getValue();
        if (value.length() > 0) {
            // Check for authentication command: format "AUTH:<token>"
            if (value.rfind("AUTH:", 0) == 0) {
                std::string receivedToken = value.substr(5);
                if (receivedToken == EXPECTED_PAIRING_TOKEN) {
                    clientAuthenticated = true;
                    Serial.println("BLE Client authenticated successfully!");
                    uint8_t ack = 0xAA; // Auth OK ack
                    pCharacteristic->setValue(&ack, 1);
                    pCharacteristic->notify();
                    return;
                } else {
                    Serial.println("SECURITY ALERT: Invalid BLE token received! Rejecting client.");
                    clientAuthenticated = false;
                    BLEComm::disconnect();
                    return;
                }
            }
            Serial.printf("Command received (len %d)\n", value.length());
        }
    }
};

class MyServerCallbacks: public BLEServerCallbacks {
    void onConnect(BLEServer* pServer) {
        deviceConnected = true;
        clientAuthenticated = false; // Must authenticate before receiving video
        connectTimestamp = millis();
        Serial.println("BLE Device Connected. Awaiting authentication challenge...");
    }

    void onDisconnect(BLEServer* pServer) {
        deviceConnected = false;
        clientAuthenticated = false;
        Serial.println("BLE Device Disconnected. Secure session cleared.");
        pServer->startAdvertising(); // restart advertising
    }
};

void BLEComm::init() {
    BLEDevice::init("VisionAid Glasses (Secure)");
    
    // Enable BLE Security Manager (Secure Connections + Bonding)
    BLEDevice::setEncryptionLevel(ESP_BLE_SEC_ENCRYPT);
    BLEDevice::setSecurityCallbacks(new MySecurityCallbacks());

    BLESecurity *pSecurity = new BLESecurity();
    pSecurity->setAuthenticationMode(ESP_LE_AUTH_REQ_SC_BOND);
    pSecurity->setCapability(ESP_IO_CAP_NONE);
    pSecurity->setInitEncryptionFlag(ESP_BLE_ENC_KEY_MASK | ESP_BLE_ID_KEY_MASK);

    pServer = BLEDevice::createServer();
    pServer->setCallbacks(new MyServerCallbacks());
    
    BLEService *pService = pServer->createService(SERVICE_UUID);
    
    // Video streaming characteristic (Notify)
    pFrameChar = pService->createCharacteristic(
                      CHARACTERISTIC_FRAME,
                      BLECharacteristic::PROPERTY_NOTIFY
                    );
    pFrameChar->addDescriptor(new BLE2902());
    
    // Command characteristic (Write/Read/Notify)
    pCmdChar = pService->createCharacteristic(
                      CHARACTERISTIC_CMD,
                      BLECharacteristic::PROPERTY_READ |
                      BLECharacteristic::PROPERTY_WRITE |
                      BLECharacteristic::PROPERTY_NOTIFY
                    );
    pCmdChar->setCallbacks(new CommandCallbacks());
    pCmdChar->addDescriptor(new BLE2902());
    
    pService->start();
    
    // Start advertising
    BLEAdvertising *pAdvertising = BLEDevice::getAdvertising();
    pAdvertising->addServiceUUID(SERVICE_UUID);
    pAdvertising->setScanResponse(true);
    pAdvertising->setMinPreferred(0x06);
    pAdvertising->setMinPreferred(0x12);
    BLEDevice::startAdvertising();
    Serial.println("Secure BLE Ready and Advertising.");
}

void BLEComm::process() {
    // Enforce security timeout: if client connected but failed to authenticate within 10s, kick it!
    if (deviceConnected && !clientAuthenticated) {
        if (millis() - connectTimestamp > AUTH_TIMEOUT_MS) {
            Serial.println("SECURITY ALERT: Client authentication timed out. Disconnecting rogue device.");
            BLEComm::disconnect();
        }
    }
}

void BLEComm::disconnect() {
    if (pServer) {
        // Disconnect all clients
        pServer->disconnect(0);
        deviceConnected = false;
        clientAuthenticated = false;
    }
}

void BLEComm::sendFrame(const uint8_t* data, size_t len) {
    // Critical safety check: NEVER transmit camera frames to an unauthenticated party
    if (!deviceConnected || !clientAuthenticated) return;
    
    const size_t MTU = 500;
    uint16_t totalChunks = (len + MTU - 1) / MTU;
    
    uint8_t buffer[MTU + 4];
    
    for (uint16_t i = 0; i < totalChunks; i++) {
        // Re-check authentication in case session terminated mid-frame
        if (!deviceConnected || !clientAuthenticated) return;

        size_t offset = i * MTU;
        size_t chunkSize = (offset + MTU > len) ? (len - offset) : MTU;
        
        buffer[0] = (i >> 8) & 0xFF;
        buffer[1] = i & 0xFF;
        buffer[2] = (totalChunks >> 8) & 0xFF;
        buffer[3] = totalChunks & 0xFF;
        
        memcpy(buffer + 4, data + offset, chunkSize);
        
        pFrameChar->setValue(buffer, chunkSize + 4);
        pFrameChar->notify();
        
        delay(10);
    }
}

void BLEComm::sendCommand(uint8_t cmd) {
    if (!deviceConnected || !clientAuthenticated) return;
    pCmdChar->setValue(&cmd, 1);
    pCmdChar->notify();
}

bool BLEComm::isConnected() {
    return deviceConnected;
}

bool BLEComm::isAuthenticated() {
    return clientAuthenticated;
}
