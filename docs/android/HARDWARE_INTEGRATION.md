# BLE & Physical Computing Hardware Integration 🔌

This document provides developer guidelines for Parakram's peer-to-peer communication stack, physical computing pin configurations, and built-in hardware sandbox emulator.

---

## 1. Bluetooth Low Energy (BLE) State Machine

Parakram's Bluetooth communication is managed by `TinkrBleManager`, which exposes states as reactive Kotlin `StateFlow` structures.

```text
 ┌─────────────────────────────────────────────────────────┐
 │               BleConnectionState.Disconnected           │
 └────────────────────────────┬────────────────────────────┘
                              │
                              ▼ (User taps 'Connect')
 ┌─────────────────────────────────────────────────────────┐
 │               BleConnectionState.Connecting             │
 └────────────────────────────┬────────────────────────────┘
                              │
                              ├─► Clears standard Android GATT caches
                              ├─► Requests max MTU (247 bytes)
                              │
                              ▼ (Connection Successful)
 ┌─────────────────────────────────────────────────────────┐
 │               BleConnectionState.Connected              │
 │               (Exposes BoardEntity manifest)            │
 └─────────────────────────────────────────────────────────┘
```

The system uses three connection states:
1.  **`BleConnectionState.Disconnected`**: The default state. Scanning can run when disconnected.
2.  **`BleConnectionState.Connecting`**: Temporary state while establishing a connection.
3.  **`BleConnectionState.Connected(val board: BoardEntity)`**: A connection is active. The connected board object provides a serialized `HardwareManifest` detailing available capabilities.

---

## 2. Samsung and Xiaomi Android GATT Optimizations

Working with Android’s Bluetooth Low Energy stack can be unreliable due to manufacturer-specific differences in connection handling. Parakram implements several robust workarounds to handle these discrepancies:

### 2.1 Enforcing Custom Transport Layers
On several Samsung and Xiaomi models, connecting to dual-mode Bluetooth BR/EDR and BLE devices can cause GATT connections to stall. Parakram resolves this by forcing a low-energy transport channel on API 23+:
```kotlin
// Under-the-hood implementation within the connection pipeline
device.connectGatt(context, false, gattCallback, BluetoothDevice.TRANSPORT_LE)
```

### 2.2 Reflective GATT Cache Clearing
Android keeps a local cache of BLE attributes. If a microcontroller's firmware changes and updates its services, Android may read outdated descriptors. Parakram forces a cache clear using reflection:
```kotlin
private fun refreshDeviceCache(gatt: BluetoothGatt): Boolean {
    return try {
        val refreshMethod = gatt.javaClass.getMethod("refresh")
        val result = refreshMethod.invoke(gatt) as Boolean
        Log.d("ParakramBLE", "GATT Cache clear method call returned: $result")
        result
    } catch (e: Exception) {
        Log.e("ParakramBLE", "Failed to force clear GATT cache: " + e.message)
        false
    }
}
```

### 2.3 MTU (Maximum Transmission Unit) Negotiation
By default, BLE packets are limited to 23 bytes. To support complex JSON payloads (like those used for displaying text or sending OTA firmware bundles), Parakram requests an expanded MTU of 247 bytes:
```kotlin
gatt.requestMtu(247)
```
Upon success, Parakram updates its logging feed to confirm that payloads up to 247 bytes are supported.

---

## 3. The "Dumb Library" Stack Philosophy: Phone as Brain, Board as Body 🧠⚡🔌

Parakram is architected around a unified high-performance paradigm: **the phone acts as the central execution brain, while the microcontroller board remains a lightweight physical extension of physical I/O registers.** Rather than generating complex processing code on-chip, we offload resource-intensive workloads (rendering graphics, processing LLMs, recognizing voice commands, managing wireless routing, and charting signals) directly to the smartphone.

This design is implemented by integrating a series of specialized, native protocol handlers directly into the Parakram companion app:

```text
 ┌────────────────────────────────────────────────────────┐
 │                      PARAKRAM APP                      │
 │          (Jetpack Compose GPU Renders, NLP)            │
 └──────┬───────────────────┬───────────────────┬─────────┘
        │ (DumbDisplay IP)  │ (Phyphox BLE)     │ (Audio Streams)
        ▼                   ▼                   ▼
 ┌──────────────┐    ┌──────────────┐    ┌──────────────┐
 │ HW Display   │    │ HW Sensors   │    │ Audio Inputs │
 │ LCD/ST7789   │    │  (I2C/ADC)   │    │ & Speakers   │
 └──────────────┘    └──────────────┘    └──────────────┘
```

---

### 3.1 Display Output — DumbDisplay Protocol Native Server
*   **Original Library Reference**: `github.com/trevorwslee/Arduino-DumbDisplay`
*   **Architectural Concept**: The board announces its connected TFT/LCD configurations. The Parakram app intercepts the request, constructs the interface using Android Jetpack Compose's GPU render tree, converts complex layouts into compact serialized drawing directives, and streams them over Low-Energy BLE or TCP/WiFi.
*   **Engineering Impact**: Zero local layout memory consumption on-chip. The master ESP32 has no font indices, geometry math, or visual widget logic — it simply draws direct pixel arrays received from the phone's rendering pipeline.

### 3.2 Audio in/out — Phil Schatzmann's audio-tools + ESP32-A2DP
*   **Original Library Reference**: `github.com/pschatzmann/arduino-audio-tools` & `ESP32-A2DP`
*   **Architectural Concept**: Sound is represented as continuous stream structures connected end-to-end. Parakram converts high-frequency voice captures and speech synthesizers into UDP/TCP audio pipes.
*   **Engineering Impact**:
    *   **I2S Microphone (INMP441) Input**: Streams raw PCM audio packets straight to Parakram. The phone performs speech analysis via SpeechRecognizer, entirely avoiding on-chip DSP limits.
    *   **Speaker Output (PAM8403) Stream**: The companion app synthesizes text response vocals (TTS) and sends audio bytes over UDP to be played immediately by the board's DAC registers.

### 3.3 Phone Sensors to Board — Custom Phyphox BLE Bridge
*   **Original Library Reference**: `github.com/phyphox/phyphox-arduino`
*   **Architectural Concept**: Parakram implements an in-app emulator matching Phyphox's GATT characteristic signatures. The phone reads its active internal hardware sensors (GPS coordinates, accelerometers, gyroscopes, magnetometers) and pushes these values back to the board.
*   **Engineering Impact**: Microcontroller designs can access full GPS navigation coordinates and precise heading values over BLE without requiring dedicated external hardware shields.

### 3.4 Camera Streaming — ESP32_USB_Stream Host Integration
*   **Original Library Reference**: `github.com/esp-arduino-libs/ESP32_USB_Stream`
*   **Architectural Concept**: Direct USB Video Class (UVC) and USB Audio Class (UAC) pipelines.
*   **Engineering Impact**: Users connect generic, inexpensive USB webcams directly to the ESP32-S3's native USB OTG pins. The board streams raw frame formats (MJPEG) over WiFi to the Parakram app for real-time processing and analyzer mapping.

### 3.5 OTA Microcode Delivery — ElegantOTA / AsyncElegantOTA
*   **Original Library Reference**: `github.com/ayushsharma82/ElegantOTA`
*   **Architectural Concept**: Simplified firmware deployment via HTTP.
*   **Engineering Impact**: Parakram contains a background compilation tool that delivers finished binaries directly to the ESP32's built-in memory partitions. This minimizes the risk of partition corruption on the microcontroller.

### 3.6 Automated WiFi Provisioning — WiFiManager / IotWebConf
*   **Original Library Reference**: `github.com/tzapu/WiFiManager` & `IotWebConf`
*   **Architectural Concept**: Automating network discovery and setup.
*   **Engineering Impact**: Unconfigured boards start a soft access point (SoftAP). The Parakram app automatically identifies this network, requests the user's home WiFi credentials, and transfers them over to the board to establish a permanent network link.

---

## 4. Peripheral Hardware Registers & Pin Maps

The standard Parakram software payload matches a high-performance ESP32-S3 microcontroller developer layout, mapped as follows:

| Target Pin Name | Output Pin | Interface | Physical Function | Supported Command Payload |
| :--- | :---: | :---: | :--- | :--- |
| **GPIO_13_LED** | Pin 13 | GPIO | Diagnostic Status LED on board | `{"cmd": "set_gpio", "pin": 13, "value": 0/1}` |
| **RELAY_12** | Pin 12 | GPIO | Relayed Water Pump irrigation pulse | `{"cmd": "set_gpio", "pin": 12, "value": 0/1}` |
| **PWM_SERVO_15**| Pin 15 | PWM | High-torque articulating mechanical sweep| `{"cmd": "servo_angle", "value": 0-180}` |
| **BUZZER_14** | Pin 14 | DAC | Emergency warn siren Piezo acoustic sound| `{"cmd": "play_tone", "frequency": 100-3000}` |
| **TFT_ST7789** | Bus SPI| TFT | ST7789 TFT display panel text buffer | `{"cmd": "display", "text": "Message Text"}` |

---

## 5. Hardware Emulator: Real-time Telemetry Calculations

When **Simulator Mode** is active, `TinkrBleManager` runs an active coroutine loop. It simulates sensor values, feeding data to Room database tables and the user interface at 1.5-second intervals.

Simulated values fluctuate dynamically according to the following formulas:

### 5.1 Ambient Temperature Layout
Temperature values fluctuate around a baseline using a randomized walk model, limited to a realistic range of 18.0°C to 39.0°C:
$$T_{new} = T_{old} + \delta \quad \text{where} \quad \delta \in [-0.2, +0.2] \quad \text{and} \quad T_{new} \in [18.0, 39.0]$$

### 5.2 Soil Moisture Decay
Soil moisture decays over time to simulate water absorption and evaporation:
$$M_{new} = \max(15.0, M_{old} - 0.15)$$
When soil moisture falls below 15.0%, the simulator triggers a warning log:
`"ALERT: Soil Moisture critical [15%]!"`

If water is sprayed during this period (e.g., if the user prompts the AI to irrigate the garden, or triggers the relay at Pin 12), moisture spikes to help test system response:
$$M_{irrigated} = \min(99.0, M_{old} + 25.0)$$

### 5.3 Ambient Light Intensity
Light values fluctuate to simulate cloud cover, day/night cycles, or sudden shadow events:
$$L_{new} = \max(10.0, \min(1200.0, L_{old} + \omega)) \quad \text{where} \quad \omega \in [-20.0, +20.0]$$

### 5.4 Carbon Dioxide Levels (CO2 Air Quality)
CO2 levels drift between standard indoor baselines (380 ppm) and higher values (950 ppm):
$$C_{new} = \max(380.0, \min(950.0, C_{old} + \theta)) \quad \text{where} \quad \theta \in [-4.0, +4.0]$$

---

## 6. Firmware Updates via Over-The-Air (OTA) Handshakes

Parakram's BLE protocol supports flashing updated firmware binaries remotely without needing physical connections or cables.

1.  **Command Dispatched**: High-level systems send a command packet payload:
    `{"cmd": "flash_ota"}`
2.  **Data Transmission**: The firmware file is split into 240-byte chunks and sent over BLE.
3.  **Completion and Reset**: Once transmission reaches 100%, the Board resets its instruction register, runs self-diagnostics, clears caches, and rebuilds BLE connections.
