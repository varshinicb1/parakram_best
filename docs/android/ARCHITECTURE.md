# Parakram System Architecture Overview 📐

Parakram's design isolates hardware, communication protocols, AI generation, and user interface states into clean, decoupled layers. This separation prevents blocking the UI thread during high-frequency BLE sensor streams or heavy AI network requests.

---

## 1. Architectural Layers & Relationships

The application is structured into eight core functional layers:

```text
       ┌─────────────────────────────────────────────────────────┐
       │               PRESENTATION (Jetpack Compose)            │
       └────────────────────────┬────────────────────────┬───────┘
                                │                        │
                                ▼                        ▼
       ┌────────────────────────────────▲──────┐  ┌──────▲───────────────┐
       │          AI / AGENT SERVICE    │      │  │  HARDWARE ENGINE     │
       │          (Reflective Exec)     │      │  │ (ParakramBleManager) │
       └────────────────────────┬───────┘      │  └──────┬───────────────┘
       ┌────────────────────────▼──────────────┐  │      │
       │               DATA STORE              │◄─┘      ▼
       │         (Room DB / DataStore)         │  ┌──────────────────────┐
       └───────────────────────────────────────┘  │   PROTOCOL LAYER     │
                                                  │ (Moshi JSON Adapters)│
                                                  └──────┬───────────────┘
                                                         │
                                                         ▼
                                                  ┌──────────────────────┐
                                                  │  FIRMWARE / HARDWARE │
                                                  │  (Real / Simulated)  │
                                                  └──────────────────────┘
```

---

## 2. Layer Deep-Dive

### 2.1 Presentation Layer (Jetpack Compose UI)
The presentation layer contains a set of composable views, utilizing standard Material 3 components styled around a dark theme with high-contrast accent signals (**TinkrOrangeGlow**, **TinkrSlateDarkBg**, and **TinkrCardDark**).

*   **`MainActivity`**: This is the orchestrator. It manages edge-to-edge system insets, boots the `SettingsRepository`, collects the configuration flows (onboarding finish status, active languages), and swaps screens using an `AnimatedContent` cross-fade transition.
*   **`HomeScreen`**: Features dynamic dashboard cards showing live telemetry statistics (Temperature, Light Intensity, Soil Hydration, Carbon Dioxide). It integrates a historical chart element, an active command-log feed displaying recent updates from the BLE board, and action buttons for testing components.
*   **`BuildScreen`**: Provides a split workspace including a raw code editor interface, simulated block-based visual scripting modules, a diagnostic monitor, and a microphone prompt trigger.
*   **`ProjectsScreen`**: Serves as a sandbox catalog, allowing creators to boot scaffolded profiles (such as smart watering setups or customized greenhouse nodes) which write starter code blocks into the Room database.
*   **`BoardsScreen`**: Displays BLE scan cards, RSSI signal indicators, paired device properties, and a custom interactive Wi-Fi routing provision card.
*   **`AISheet`**: A dynamic sliding bottom sheet carrying the continuous chatbot history. It displays generated codes, explains actions being dispatched, and houses the system's prompt triggers.

### 2.2 Domain & Core Logic Layer
The core business logic coordinates states, tracks setting changes, and handles reactive conditions:
*   **State Propagation**: Views do not modify states directly; instead, they fire commands into repositories or managers and collect downstream occurrences through asynchronous Kotlin `StateFlow` and `SharedFlow` objects.
*   **`TinkrTranslations`**: An in-memory, localized dictionary containing structured strings mapping 4 languages (English, Spanish, German, French). It processes tokens using standard parameters and operates synchronously, eliminating lag when swapping translation scopes on the fly.

### 2.3 Data Persistence Layer (Room & Preferences)
Parakram persists settings, project files, telemetry readings, and chat transcripts locally.
*   **DataStore Preferences (`SettingsRepository`)**: A robust, lightweight key-value store. It handles language choices, active board addresses, simulator toggles, and flags indicating if AI models have been loaded. This file uses Kotlin flows mapped through helper keys (`stringPreferencesKey`, `booleanPreferencesKey`).
*   **Room Database (`TinkrDatabase`)**: Consists of four SQLite table schemas:
    1.  `BoardEntity`: Real or simulated peripheral specifications, including BLE MAC address, board color, configured firmware level, and I/O registers capabilities stored in an optimized JSON manifest.
    2.  `ProjectEntity`: Name, description, active Arduino C/C++ code, visual Blockly XML structure, and configuration metadata.
    3.  `SensorLogEntity`: A database tracking values and sensor keys to enable historical plotting.
    4.  `AIChatEntity`: A database keeping history clean, recording roles (`user` or `assistant`), modes, explanations, and serialized tool outputs.

### 2.4 Hardware Layer (`TinkrBleManager`)
The connection engine wraps Android's Bluetooth Low Energy stack in safety wrappers.
*   **Robust GATT Connection Protocols**: Features connection parameters customized for Samsung and Xiaomi devices. It forces a clean GATT cache scrub through Java reflection, requests high-throughput MTU negotiation up to 247 bytes, and binds hooks under separate coroutine supervisors to handle reconnections.
*   **Virtual Hardware Core Sandbox**: If no hardware is paired, the BLE manager runs a client-side digital twin. An active ticker task uses randomized math to decay reading levels (like soil moisture evaporating) and logs results directly to Room, matching the behavior of actual peripheral chips.

### 2.5 AI & Autonomous Agent Layer (`TinkrAIService`)
Parakram's standout feature is its recursive autonomous agent loop. It interprets queries, compiles a plan of actions, and executes hardware tools sequentially using reflection on Kotlin interfaces.
*   **Reflective Tool Binding (`@Tool`, `@ToolParam`)**: Hardware functions are declared directly as clean annotated interface methods. The service parses these runtime attributes, formats schemas for LLMs, and invokes commands when the model returns valid JSON matching those definitions.
*   **Dual Intelligence Core**: If a cloud-configured `GEMINI_API_KEY` is present, Parakram invokes Gemini 3.5 Flash via standard REST calls. If offline, the service falls back to a simulated local Gemma runtime.

### 2.6 Protocol Layer (`TinkrProtocol`)
The protocol defines standard formatting schemas, ensuring secure communication between Android and external hardware.
*   **`SensorStreamMessage`**: A shortened packet payload struct (`t`: timestamp, `s`: sensor name, `v`: value, `u`: unit) that decreases transmission size over BLE.
*   **`CommandMessage`**: The unified packet layout for outgoing microcontroller actions (`cmd` category, `pin` identifier, I/O pin `mode`, `value` configuration, and string `text`/`frequency` values).
*   **`HardwareManifest`**: A hardware profile schema used to identify capabilities dynamically. It catalogs diagnostic modules, available analog/digital pin maps, and LCD panels connected to the board, allowing Parakram's UI to self-generate corresponding layouts on connection.

---

## 3. Core Threading & Coroutine Dispatch Structures

To maintain 60FPS UI performance and high-speed BLE communication, Parakram operates across three distinct thread pools:

```text
┌───────────────────────────┐ ◄─── High-priority UI Renders, touch targets & animation values
│    Main Dispatcher Pool   │ 
└─────────────┬─────────────┘
              │ (Non-blocking callbacks)
              ▼
┌───────────────────────────┐ ◄─── Background DB queries, Network REST calls & JSON parsing
│     IO Dispatcher Pool    │      (Prevents UI stalls during heavy operations)
└─────────────┬─────────────┘
              │ (Separated asynchronous contexts)
              ▼
┌───────────────────────────┐ ◄─── Parallel mathematical calculations, Bluetooth scanning,
│   Default Dispatcher Pool │      and the virtual hardware emulator ticker
└───────────────────────────┘
```

1.  **Main/UI Thread**: Jetpack Compose state-collection and layout rendering.
2.  **Dispatchers.IO**: Heavy SQLite writes, DataStore modifications, and OkHttp requests to the generative API endpoint.
3.  **Dispatchers.Default & SupervisorJob**: Active BLE scan filters, telemetry parsing, and the local simulator loop running in the background.

---

## 4. Architectural State Flow Timeline

The following sequence illustrates what occurs when a user triggers an action (e.g., prompting the AI to "Water the plant"):

```text
[User Type Prompt] ──► AISheet (Captures Text)
                             │
                             ▼
                    TinkrAIService.runPrompt(prompt, mode)
                             │
                             ├─► [Network/REST API] Cloud Gemini / Local Simulation
                             │   (Generates JSON Action sheet with Tool calls)
                             │
                             ▼
                    executeToolReflective("writeGPIO", "{\"pin\":12, \"value\":1}")
                             │
                             ▼
                    TinkrBleManager.processCommand(CommandMessage(cmd="set_gpio", pin=12, value=1))
                             │
                             ├─► [Physical BLE Update] (Sends Command to Microcontroller)
                             ├─► [Virtual Twin Simulation] (Spikes Simulated Moisture %)
                             │
                             ▼
                    TinkrDatabase.sensorLogDao().insertLog() & aiChatDao().insertChat()
                             │
                             ▼
[Reactive State Changes] ◄─── UI collects changes via StateFlow and updates elements
```

By adhering to this state-driven pipeline, Parakram remains robust, predictable, and simple to test or extend.
