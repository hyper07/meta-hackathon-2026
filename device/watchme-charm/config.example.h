// Copy to config.h (not committed) and fill in.
#pragma once

// 0: Wi-Fi straight to the server. 1: over the USB cable through device/bridge.py on the Mac
// (for a board whose Wi-Fi can't reach the network, or to keep it tethered for a demo).
#define LINK_USB 0

#define WIFI_SSID     "your-2.4GHz-wifi"   // the ESP32-C6 joins 2.4 GHz networks only
#define WIFI_PASSWORD "your-wifi-password"

// The Mac running the Watch Me server with `cd app && ./run.sh --lan` (it prints this address).
#define SERVER_HOST   "192.168.1.20"
#define SERVER_PORT   8000

#define SPEAKER_VOLUME 75   // 0-100, the speaker on the MX1.25 connector
#define MIC_GAIN_DB    ES8311_MIC_GAIN_24DB
