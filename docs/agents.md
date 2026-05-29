# Parakram Agent Operating Instructions

**Version:** 2.0
**Purpose:** Instructions for any AI agent working inside the `parakram_best` unified repository.

---

## Core Philosophy

**Parakram = Phone as Brain + Board as Body + Zero Driver Hell**

The Android app is the intelligent brain.
The ESP32-S3 factory firmware is the reliable body.
The user configures **intent**, not drivers.

---

## Repository Layout

| Directory | Purpose | Tech |
|---|---|---|
| `android/` | Primary Android app (BLE, AI, UI) | Kotlin, Compose |
| `android/vidyuthlabs-app/` | Extended Android app (billing, fleet) | Kotlin, Compose |
| `backend/` | Rust cloud backend | Rust, axum |
| `firmware/` | ESP32-S3 firmware (59 drivers, VM) | C, ESP-IDF |
| `desktop/app/` | Tauri desktop IDE | React 19, TypeScript |
| `desktop/services/` | Python backend services | FastAPI |
| `ios/` | iOS app | SwiftUI |
| `ai/codelm/` | CodeLM agent spec | Spec document |
| `rtos/` | Experimental RTOS kernel | Rust |
| `shared/` | Protocols, schemas | OpenAPI |
| `deploy/` | Cloud deployment | K8s, Azure, AWS |
| `playground/` | Web playground | Vanilla JS |
| `admin/` | Admin panel | Vanilla JS |

---

## Mandatory Workflow

### Step 1: Understand the Scope

Before modifying any component, understand how it fits in the overall pipeline:

```
User Intent → LLM (backend/src/llm/) → IR (backend/src/ir/)
→ Bytecode (backend/src/compiler/) → Firmware VM (firmware/main/runtime/vm.c)
→ Hardware Drivers (firmware/main/drivers/)
```

### Step 2: Never Delete Without Approval

- Do not delete any file or folder in the first pass.
- Propose migration or archiving instead.

### Step 3: Leverage OSS

When you need audio, display, wake word, OTA, Lua, I2C detection — first check if an existing high-quality OSS repo solves it. See `scripts/clone_oss_deps.sh`.

### Step 4: Decision Framework

1. Does existing Parakram code already solve 60%+ of this?
2. Does a well-maintained OSS repo solve 80%+ of it?
3. Can we combine (1) + (2)?
4. Only then write new code from scratch.

---

## Technical Priorities

### Factory Firmware (Highest Priority)

1. **Hardware Manifest** — Boot-time peripheral auto-detection → JSON over BLE
2. **Audio Pipeline** — INMP441 → UDP stream to Android app + speaker playback
3. **DumbDisplay Server** — Phone renders, board receives pixels
4. **BLE OTA** — Reliable firmware updates from the app
5. **Wake Word** — Always-listening, low-power wake word
6. **Lua Sandbox** — Safe user scripting environment

### OSS Libraries to Leverage

- Audio: `pschatzmann/arduino-audio-tools`
- Display: `trevorwslee/Arduino-DumbDisplay`
- Phone Sensors → Board: `phyphox/phyphox-arduino`
- Wake Word: `kahrendt/esphome-on-device-wake-word`
- BLE OTA: `gb88/BLEOTA`
- Lua: `whitecatboard/Lua-RTOS-ESP32` (interpreter only)
- I2C Detection: `Sensirion/arduino-upt-i2c-auto-detection`

---

## Coding Standards

- **Rust**: `thiserror` for errors, `tracing` for logs, no `unwrap()` in prod paths
- **Firmware C**: no dynamic allocation in hot paths, no `malloc` in VM, implement `driver_vtable_t`
- **Kotlin**: Compose best practices, coroutines for async, Room for persistence
- **TypeScript**: React 19, Zustand for state, Tailwind for styling
- **Python**: FastAPI, type hints, Pydantic models

---

## Final Goal

A unified `parakram_best` repository where:

- Cloning + building gives a working Factory Firmware that talks to the Android app
- Every standard peripheral "just works" with minimal or zero user code
- The AI agent in the app can configure real hardware behavior
- All previous Parakram work is preserved and properly integrated
