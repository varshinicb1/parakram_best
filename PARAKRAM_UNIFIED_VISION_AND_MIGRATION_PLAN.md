# Parakram Unified Vision & Migration Plan

**Version:** 1.0  
**Date:** May 29, 2026  
**Goal:** Turn all existing Parakram pieces + Edgehax S3 hardware into **one best-in-class, production-ready platform**.

---

## Executive Summary

Parakram is becoming **the phone-brained embedded platform**.

**Core Idea:**
- The **Android app** (already built, named "parakram") is the brain.
- The **ESP32-S3 N16R8 board** (Edgehax hardware) is the body.
- A **factory firmware** on the board makes every peripheral "just work" (mic, speaker, display, sensors) with **zero driver code** from the user.
- The user configures behavior via natural language, visual blocks, or simple Lua in the app.
- The AI agent (already partially in the app) translates intent into real hardware behavior over BLE + UDP.

This document is the **complete blueprint** to unify everything without losing any existing work.

---

## Current State Audit (What We Have Today)

### Existing Parakram Repos (from your GitHub)

| Repo | Status | What It Contains | Keep / Migrate / Deprecate |
|------|--------|------------------|---------------------------|
| **Parakram_new** | Excellent foundation | Full backend API (intent → IR → compile → deploy), OTA, billing, driver marketplace, fleet management, multi-platform support | **Core backend** — migrate into `backend/` |
| **parakram** | Very good UX | Rich Tauri + React desktop app with visual designer, Blockly, Wokwi simulator, calibration, telemetry | **Desktop experience** — migrate key UI patterns into Android app or keep as advanced desktop client |
| **Parakram Android app** (your APK) | Already built | BLE manager, AI agent shell, simulator, UI framework, command protocol | **The Brain** — this is the main client. Do **not** touch core structure yet. |
| **Parakramgame** | Small | Firmware coding game for ESP32 | Deprecate or turn into tutorial mode inside app |
| **parakram-os** | Tiny | Early Rust OS experiment | Deprecate — move useful low-level ideas into factory firmware |
| **ParakramCodeLM** | Tiny | Early code LLM idea | Absorb into AI agent prompts |

### The Missing Piece (The Big Gap)
**Factory Firmware** on the ESP32-S3 N16R8 that:
- Auto-detects connected hardware (mic, speaker, display, sensors)
- Makes them "just work" over BLE/UDP with the Android app
- Runs wake word, audio streaming, DumbDisplay-like rendering, Lua sandbox, BLE OTA
- Talks to the existing Parakram Android app

This is what we will build.

---

## Unified Vision: Parakram = Phone as Brain + Board as Body

### The Four Layers (Final Architecture)

1. **Parakram Android App** (Brain)
   - Already exists
   - BLE central + UDP receiver
   - AI agent (intent → config/commands)
   - Visual editor / Blockly / Lua editor
   - DumbDisplay server (phone renders, board just blits)
   - Vosk offline STT, TTS streaming
   - Phyphox BLE bridge (phone sensors → board)

2. **Factory Firmware** (Body — The New Core)
   - Runs on ESP32-S3 N16R8 (16MB Flash + 8MB PSRAM)
   - Auto-detects peripherals on boot → sends `HardwareManifest` over BLE
   - Pre-compiled drivers for INMP441, MAX98357A, ST7789, I2C sensors, etc.
   - Audio pipeline (mic → UDP → app → TTS → speaker)
   - Wake word (always listening, 10ms inference)
   - Lua sandbox for user scripts
   - BLE OTA + ElegantOTA fallback
   - WiFi provisioning via WiFiManager + encrypted provisioning

3. **Shared Protocols** (The Glue)
   - BLE GATT services (already partially defined in your docs)
   - UDP audio streaming
   - DumbDisplay command protocol (phone → board pixels)
   - `HardwareManifest` JSON over BLE

4. **AI Agent Layer** (The Intelligence)
   - Already partially in Android app
   - Will generate firmware configs, Lua scripts, or direct hardware commands from natural language

---

## Migration & Combination Plan (Step-by-Step)

### Phase 0: Audit & Categorize (Do NOT Delete Anything Yet)

**Agent Instruction (see agents.md):**
When you start working on this repo, you **must** follow this exact order:

1. Run a full file tree + summary of every `.c`, `.cpp`, `.h`, `.kt`, `.java`, `.py`, `.ts`, `.tsx` file.
2. Categorize every file into:
   - `firmware/` (ESP32 code)
   - `android/` (Kotlin/Compose)
   - `shared/` (protocols, models, IR)
   - `ai/` (prompts, agent logic)
   - `desktop/` (Tauri/React — keep or migrate)
   - `backend/` (from Parakram_new)
3. For every major function/class, write a one-sentence purpose.
4. Identify overlaps and conflicts.
5. Only after the full audit report is written and reviewed, propose unification.

### Phase 1: Create the Unified Repo Structure (Week 1)

Recommended folder structure for `parakram_best`:

```
parakram_best/
├── firmware/                    # NEW — Factory firmware (biggest missing piece)
│   ├── src/
│   │   ├── main/
│   │   ├── audio/               # INMP441 + MAX98357A pipeline
│   │   ├── display/             # DumbDisplay server implementation
│   │   ├── ble/                 # GATT services + OTA
│   │   ├── lua/                 # Lua sandbox + hardware API
│   │   ├── wake_word/           # TFLite wake word
│   │   ├── manifest/            # I2C auto-detection + HardwareManifest
│   │   └── tasks/               # FreeRTOS task topology
│   ├── partitions.csv
│   └── CMakeLists.txt
├── android/                     # Your existing Parakram APK source
│   ├── app/
│   └── ...
├── backend/                     # Migrated from Parakram_new
├── desktop/                     # Migrated from "parakram" Tauri app (optional advanced client)
├── shared/                      # Protocols, models, IR definitions
│   ├── proto/
│   ├── models/
│   └── agents/
├── ai/                          # Prompts, model hub references, agent logic
├── docs/
│   ├── agents.md                # ← This file (agent instructions)
│   ├── ARCHITECTURE.md
│   └── MIGRATION.md
├── scripts/
│   └── clone_oss_deps.sh        # Script to clone all referenced OSS repos
└── README.md
```

### Phase 2: Integrate Existing Code (No Deletion)

- Move useful backend code from **Parakram_new** → `backend/`
- Move visual designer + Blockly logic from **parakram** desktop app → `android/` or `shared/`
- Keep the entire existing Android app structure in `android/`
- Extract protocol definitions from your 4 pasted docs into `shared/`

### Phase 3: Build the Factory Firmware (The Critical Path)

This is where we close the gap.

Use the OSS arsenal from the previous research (I already prepared a full list in the conversation history). Key repos to integrate:

- `pschatzmann/arduino-audio-tools` → Audio pipeline
- `trevorwslee/Arduino-DumbDisplay` → Display (implement server side in Android + board client)
- `phyphox/phyphox-arduino` → Phone sensor bridge
- `kahrendt/esphome-on-device-wake-word` + `espressif/esp-tflite-micro` → Wake word
- `gb88/BLEOTA` → BLE OTA
- `whitecatboard/Lua-RTOS-ESP32` (just the interpreter) → Lua sandbox
- `Sensirion/arduino-upt-i2c-auto-detection` + custom scanner → Hardware manifest
- `espressif/esp-box` → Reference for task topology and partition layout

### Phase 4: Make Peripherals "Just Work" (Zero Driver Hell)

This directly addresses your point about INMP441, speaker, display, etc.

**Examples of what the factory firmware + app should deliver:**

| Hardware | Today (Pain) | After Parakram (Magic) |
|----------|--------------|------------------------|
| INMP441 mic | 800+ lines of I2S + DMA + buffer management | Plug in → `HardwareManifest` shows it → Audio streams to app automatically |
| MAX98357A speaker | Write I2S output code + volume control | App sends TTS PCM → board plays it. No code. |
| ST7789 display | LVGL hell + font management + SPI tuning | App renders via DumbDisplay protocol → board just receives pixels |
| I2C sensors | Write scanner + driver for each | Boot scans I2C → sends JSON manifest → app knows exactly what's connected |
| FreeRTOS tasks | Manual priority, stack size, core pinning | Factory firmware has proven task topology (Core 0 = comms, Core 1 = audio/AI) |

---

## agents.md — Instructions for Any AI Agent Working on This Repo

**Copy the content below into `docs/agents.md`**

```markdown
# Parakram Agent Operating Instructions

You are an expert embedded + Android + AI systems architect.

## Core Rules (Never Break These)

1. **Audit First, Always**
   - Before writing or moving any code, run a complete audit of the current state of the repo.
   - List every file.
   - For every major file, write: filename + 1-sentence purpose + key functions/classes.
   - Categorize into: firmware / android / shared / ai / backend / desktop.

2. **Never Delete Without Explicit Approval**
   - Do not delete any file or folder in the first pass.
   - If something looks redundant, propose a migration path instead of deletion.
   - Only after the full audit + categorization report is created and the human confirms, proceed with cleanup.

3. **Understand Before Unifying**
   - For every function you encounter, understand:
     - What it does
     - Why it exists
     - How it can be reused or generalized in the unified architecture
   - Map every existing feature to the final vision (Phone = Brain, Board = Body, Zero Driver Hell).

4. **Leverage OSS Aggressively**
   - The `scripts/clone_oss_deps.sh` script exists for a reason.
   - When you need audio, display, wake word, OTA, Lua, I2C detection, etc. — first check if an existing high-quality OSS repo already solves it.
   - Prefer forking + adapting proven libraries over writing from scratch (especially audio and BLE OTA).

5. **Zero Driver Hell Philosophy**
   - The user should never write low-level driver code for standard peripherals.
   - If a peripheral can be auto-detected and exposed via the `HardwareManifest` + simple config, do it.
   - Examples: mic, speaker, display, common I2C sensors.

6. **Decision Making Framework**
   When deciding how to implement something, ask in this order:
   a. Does existing Parakram code (Android or backend) already do part of this?
   b. Does a high-quality OSS repo solve 80%+ of it?
   c. Can we combine (a) + (b) elegantly?
   d. Only then consider writing new code.

7. **Communication Style**
   - Always start responses with: "Audit complete. Current state: ..."
   - Then: "Proposed unification approach: ..."
   - End with: "Risks / open questions: ..."

8. **Goal**
   Build the **Factory Firmware** that makes the existing Parakram Android app come alive as a complete phone-brained embedded platform.
```

---

## Immediate Next Steps (For You / Grok)

1. Create a new GitHub repo called `parakram_best`.
2. Push this document + the `agents.md` content into `docs/`.
3. Clone the existing Parakram repos into subfolders or start migrating code according to the structure above.
4. Run the OSS clone script (I provided one in previous research).
5. Start with **Phase 1 of the firmware** (getting audio streaming + manifest working).

Would you like me to:
- Generate the full `agents.md` as a separate ready-to-paste file?
- Create the `clone_oss_deps.sh` script?
- Write the initial `ARCHITECTURE.md` with diagrams?
- Start drafting the Factory Firmware `README` with the exact task topology?

Just say the word and I'll generate the next piece.
```

This document is now ready. You can copy it into your new `parakram_best` repo.

It gives any future agent (Grok, Claude, or human) clear, strict instructions on **how to think and work** without destroying existing work.