# Parakram Agent Operating Instructions

**Version:** 1.0  
**Purpose:** This file tells any AI agent (Grok, Claude, Cursor, etc.) exactly how to behave when working inside the `parakram_best` repository.

---

## Core Philosophy

**Parakram = Phone as Brain + Board as Body + Zero Driver Hell**

The Android app is the intelligent brain.  
The ESP32-S3 factory firmware is the reliable body.  
The user configures **intent**, not drivers.

---

## Mandatory Workflow (Never Skip Steps)

### Step 1: Full Audit (Always First Action)

When you start any session, you **must** begin with a complete audit:

```bash
# Example commands you should run
find . -type f \( -name "*.c" -o -name "*.cpp" -o -name "*.h" -o -name "*.kt" -o -name "*.java" -o -name "*.py" -o -name "*.ts" -o -name "*.tsx" -o -name "*.md" \) | head -100
```

For every major file you encounter, document:

- **Filename**
- **Location** (e.g., `firmware/src/audio/`, `android/app/src/main/java/...`)
- **1-sentence purpose**
- **Key functions / classes** (list the most important 3–5)
- **Current status** (Complete / Partial / Stub / Deprecated)

**Output format required:**

```
## Audit Report - [Date]

### Firmware Layer
- `firmware/src/audio/i2s_mic.cpp` — Handles INMP441 capture and UDP streaming. Key functions: `init_i2s()`, `start_stream()`, `send_udp_packet()`. Status: Partial.

### Android Layer
- `android/app/src/main/java/com/parakram/TinkrBleManager.kt` — BLE central manager. Key functions: `connect()`, `sendCommand()`, `onCharacteristicChanged()`. Status: Good.

... (continue for all major files)
```

### Step 2: Categorize Everything

After the audit, group every piece of code into these categories:

| Category     | Description                              | Example Location      |
|--------------|------------------------------------------|-----------------------|
| `firmware`   | All ESP32 / ESP-IDF / Arduino code       | `firmware/`           |
| `android`    | Kotlin / Compose / existing app          | `android/`            |
| `shared`     | Protocols, models, IR, common types      | `shared/`             |
| `ai`         | Prompts, agent logic, model references   | `ai/`                 |
| `backend`    | Server-side API (from Parakram_new)      | `backend/`            |
| `desktop`    | Tauri/React code (from old parakram)     | `desktop/`            |
| `docs`       | Documentation and agent instructions     | `docs/`               |

### Step 3: Understand Before Touching

For every function or class you plan to modify or reuse, answer these questions internally:

1. What does this actually do?
2. Why was it written this way?
3. How does it map to the final vision (Phone = Brain, Zero Driver Hell)?
4. Can it be generalized or reused in the unified architecture?

Only after you can answer these clearly should you propose changes.

### Step 4: Unification Rules

**Golden Rules:**

- **Never delete code in the first pass.** Propose migration or archiving instead.
- Prefer **integration** over rewriting.
- When a high-quality OSS library already solves the problem well (audio, BLE OTA, wake word, DumbDisplay, etc.), **use it** rather than writing from scratch.
- The Android app is the source of truth for the user experience. Firmware must adapt to it, not the other way around.
- Every peripheral (mic, speaker, display, I2C sensor) should eventually be **auto-detected** and exposed via the `HardwareManifest` + simple configuration in the app.

### Step 5: Decision Framework (When in Doubt)

When deciding how to implement something, follow this order:

1. Does existing Parakram code (Android or backend) already solve 60%+ of this?
2. Does a well-maintained OSS repo solve 80%+ of it? (See `scripts/clone_oss_deps.sh`)
3. Can we elegantly combine (1) + (2)?
4. Only then consider writing new code from scratch.

### Step 6: Communication Style

Every response you give **must** follow this structure:

```
## Audit Status
[Brief summary of what you audited this session]

## Understanding
[What you now understand about the relevant code]

## Proposed Approach
[Clear plan — migration, integration, new code, etc.]

## Risks / Open Questions
[List any concerns]

## Next Action
[What you recommend doing next]
```

---

## Specific Technical Priorities

### Highest Priority Right Now (Factory Firmware)

The biggest missing piece is the **ESP32-S3 factory firmware** that makes the existing Android app useful.

Focus areas (in order):

1. **Hardware Manifest** — Boot-time I2C + peripheral auto-detection → JSON over BLE (`0xFF01`)
2. **Audio Pipeline** — INMP441 → UDP stream to Android app + speaker playback from app
3. **DumbDisplay Server** — Implement the server side in Android so the board can request rendered pixels
4. **BLE OTA** — Reliable firmware updates from the app
5. **Wake Word** — Always-listening, low-power wake word that activates full audio streaming
6. **Lua Sandbox** — Safe user scripting environment

### OSS Libraries We Should Leverage (Do Not Reinvent)

See the full list in previous research. Key ones:

- Audio: `pschatzmann/arduino-audio-tools`
- Display: `trevorwslee/Arduino-DumbDisplay`
- Phone Sensors → Board: `phyphox/phyphox-arduino`
- Wake Word: `kahrendt/esphome-on-device-wake-word`
- BLE OTA: `gb88/BLEOTA`
- Lua: `whitecatboard/Lua-RTOS-ESP32` (interpreter only)
- I2C Detection: `Sensirion/arduino-upt-i2c-auto-detection` + custom scanner

---

## Final Goal

Create a unified `parakram_best` repository where:

- Cloning the repo + running the build gives you a working **Factory Firmware** that talks beautifully to the existing Parakram Android app.
- Every standard peripheral "just works" with minimal or zero user code.
- The AI agent in the app can configure real hardware behavior.
- All previous Parakram work (backend, desktop patterns, protocols) is preserved and properly integrated.

---

**You are now operating under these instructions.**

When you are ready to begin work on this repository, start by saying:

> "Audit complete. Beginning full categorization..."

Then proceed according to the workflow above.