# Parakram — Unified Platform

**Phone as Brain + Factory Firmware as Body + Zero Driver Hell**

Parakram is a zero-code embedded platform by [Vidyuthlabs](https://vidyuthlabs.co.in). Users type plain English and within ~500ms the system generates, validates, and deploys executable bytecode to IoT hardware.

This monorepo unifies all Parakram components — Android app, Rust backend, ESP32 firmware, Tauri desktop IDE, iOS app, CodeLM AI, and RTOS kernel — into a single, production-ready codebase.

---

## Architecture

```
User (plain English / visual blocks / Lua)
       |
       v
Android App (Brain)          Desktop IDE (Advanced)        iOS App
  Jetpack Compose               Tauri v2 + React 19          SwiftUI
  BLE + AI Agent                 16 Spaces + Blockly          CoreBluetooth
       |                              |                         |
       v                              v                         v
                    Rust Backend (axum, port 8400)
                      LLM -> IR -> Bytecode Compiler
                      59 Driver Specs | JWT Auth | Billing
                      ROS 2 Graph Engine | Marketplace
                              |
                              v
                    ESP32-S3 Factory Firmware
                      FreeRTOS VM | 59 Drivers | OTA
                      Multi-MCU HAL (ESP32, RP2040, STM32, Arduino)
                      Auto-detect peripherals | HardwareManifest
                              |
                              v
                    Physical Hardware
                      Sensors, actuators, displays, audio
```

---

## Repository Structure

```
parakram_best/
├── android/                 # Android app (Kotlin/Compose) — The Brain
│   ├── app/                 #   Primary app (BLE, AI agent, UI)
│   └── vidyuthlabs-app/     #   Extended app (billing, fleet, marketplace)
│
├── backend/                 # Rust backend (axum)
│   ├── src/
│   │   ├── api/             #   REST API (20+ endpoint modules)
│   │   ├── compiler/        #   IR → bytecode compiler + Ed25519 signer
│   │   ├── ir/              #   Intermediate Representation schema + validator
│   │   ├── llm/             #   LLM pipeline (OpenRouter/Anthropic)
│   │   ├── drivers/         #   59 driver specs + board profiles
│   │   ├── billing/         #   Stripe billing (4 plans)
│   │   ├── marketplace/     #   Driver marketplace
│   │   ├── ros_graph/       #   ROS 2 node graph engine
│   │   └── db/              #   SQLite + migrations
│   └── Cargo.toml
│
├── firmware/                # ESP32-S3 firmware (ESP-IDF / FreeRTOS)
│   ├── main/
│   │   ├── drivers/         #   59 hardware drivers (I2C, SPI, GPIO, etc.)
│   │   ├── runtime/         #   Bytecode VM, event bus, scheduler, state store
│   │   ├── comms/           #   BLE GATT, MQTT, WiFi manager
│   │   ├── safety/          #   Fault handler, rate limiter, watchdog
│   │   └── security/        #   Ed25519 payload verification, device identity
│   ├── hal/                 #   Multi-MCU HAL (ESP32-S3, RP2040, STM32, Arduino)
│   └── ports/               #   Platform-specific build configs
│
├── desktop/                 # Tauri v2 desktop IDE
│   ├── app/                 #   Tauri + React 19 + TypeScript (16 spaces)
│   ├── services/            #   Python FastAPI backend (50+ endpoints)
│   │   ├── agents/          #     202 MISRA-compliant golden blocks
│   │   ├── api/             #     30+ route modules
│   │   ├── hardware_library/#     150+ hardware component JSONs
│   │   └── services/        #     30+ service modules
│   ├── frontend/            #   Lightweight web frontend (canvas editor)
│   ├── firmware_templates/  #   ESP32 code templates
│   └── projects/            #   Example project configs
│
├── ios/                     # iOS app (SwiftUI)
│   └── Parakram/
│       ├── API/             #   REST client
│       ├── BLE/             #   CoreBluetooth manager
│       ├── Views/           #   15 SwiftUI views
│       └── ViewModels/      #   11 view models
│
├── ai/                      # AI / CodeLM
│   └── codelm/              #   Block-token firmware synthesis model spec
│       ├── README.md        #     Full agent execution spec (2000+ lines)
│       └── sources.md       #     Authoritative corpus sources (20+ repos)
│
├── rtos/                    # Parakram OS — experimental Rust RTOS
│   ├── src/                 #   Kernel + quantum/kyber modules
│   ├── benchmarks/          #   Performance benchmarks
│   ├── patents/             #   Patent drafts + novelty reports
│   └── avr/riscv/stm32/    #   Architecture-specific affinity modules
│
├── shared/                  # Cross-platform protocols & schemas
│   └── protocols/           #   OpenAPI spec
│
├── deploy/                  # Cloud deployment configs
│   ├── kubernetes/          #   K8s manifests (deployment, HPA, ingress)
│   ├── azure/               #   Azure Container Apps (Bicep)
│   └── aws/                 #   AWS ECS Fargate task definition
│
├── docs/                    # Documentation
│   ├── architecture/        #   AI pipeline, compiler, firmware architecture
│   ├── artifacts/           #   10 detailed design documents
│   ├── android/             #   Android-specific docs
│   ├── desktop/             #   Desktop IDE docs
│   └── getting_started/     #   Setup & flasher guides
│
├── playground/              # Web playground (vanilla JS, dark SPA)
├── admin/                   # Admin panel (driver moderation, metrics)
├── landing/                 # Landing page
├── nginx/                   # Reverse proxy configs
├── prometheus/              # Monitoring config
├── tests/                   # Integration tests
├── scripts/                 # Utility scripts
├── assets/                  # Shared icons and images
├── .github/workflows/       # CI/CD (build, test, deploy)
├── docker-compose.yml       # Development
├── docker-compose.prod.yml  # Production
└── LICENSE                  # PolyForm Noncommercial 1.0.0
```

---

## Quick Start

### Backend (Rust)

```bash
cd backend
cp .env.example .env   # fill in API keys
cargo run              # dev mode on port 8400
```

### Desktop IDE (Tauri + React)

```bash
# Start the Python services backend
cd desktop/services
pip install -r requirements.txt
python main.py

# Start the Tauri desktop app
cd desktop/app
npm install
npm run dev

# Build distributable
cd desktop
python build_sidecar.py
cd app && cargo tauri build
```

### Android App

Open `android/` in Android Studio. Build and run on device/emulator.

### iOS App

Open `ios/` in Xcode. Build and run on simulator/device.

### Firmware (ESP32-S3)

```bash
cd firmware
idf.py set-target esp32s3
idf.py build
idf.py flash monitor
```

### Web Playground

Open `playground/index.html` in Chrome, or visit `http://localhost:8400` with the backend running.

### Docker (Production)

```bash
docker-compose -f docker-compose.prod.yml up --build
```

---

## Source Repos (Unified Here)

| Original Repo | Role | Location in This Repo |
|---|---|---|
| `ParakramOS-android-app` | Primary Android app (BLE, AI agent, Compose UI) | `android/` |
| `Parakram_new` | Rust backend + firmware + iOS + deploy + admin | `backend/`, `firmware/`, `ios/`, `deploy/` |
| `parakram` | Tauri desktop IDE + Python services + web frontend | `desktop/` |
| `ParakramCodeLM` | Block-token CodeLM agent spec | `ai/codelm/` |
| `parakram-os` | Experimental Rust RTOS kernel | `rtos/` |
| `Parakramgame` | Firmware coding game (deprecated) | — |

---

## Key Technical Details

### 59 Firmware Drivers

Complete ESP-IDF driver implementations for sensors, actuators, displays, and communication modules including BME280, MPU6050, INMP441, MAX98357A, ST7789, WS2812, HC-SR04, GPS NEO-6M, and more.

### 202 Golden Blocks (Desktop)

MISRA-compliant, verified code blocks across 10 categories covering sensor reading, actuator control, communication protocols, signal processing, and control theory.

### 150+ Hardware Library Components

JSON specifications for actuators, sensors, communication modules, displays, audio, and control blocks — enabling zero-code hardware configuration.

### Multi-MCU HAL

Platform Abstraction Layer supporting ESP32-S3, RP2040, STM32F4, and Arduino with a unified `parakram_pal.h` interface.

### 16 Desktop Spaces

Home, Workspace, Blocks, Visual Designer, Blockly Editor, Simulator (Wokwi), Devices, Telemetry, Debug, Calibration, Verification, Settings, Auth, Installer, Extensions, Admin.

---

## Environment Variables

| Variable | Required | Description |
|---|---|---|
| `OPENROUTER_API_KEY` | Yes (preferred) | Primary LLM — one key, 100+ models |
| `ANTHROPIC_API_KEY` | Fallback | Used if no OPENROUTER_API_KEY |
| `DATABASE_URL` | No | Default: `sqlite:parakram.db?mode=rwc` |
| `JWT_SECRET` | Yes (prod) | Base64 random string, min 32 bytes |
| `BIND_ADDR` | No | Default: `0.0.0.0:8400` |

---

## Tech Stack

- **Backend**: Rust, axum, SQLite, Ed25519 signing
- **Android**: Kotlin, Jetpack Compose, Room, BLE, Gemini API
- **iOS**: SwiftUI, CoreBluetooth, URLSession
- **Desktop**: Tauri v2, React 19, TypeScript, Tailwind, XY Flow, Three.js
- **Desktop Services**: Python, FastAPI, NumPy
- **Firmware**: C, ESP-IDF 5.1, FreeRTOS, multi-MCU HAL
- **RTOS**: Rust (experimental kernel)
- **AI**: Block-token transformer architecture (CodeLM spec)
- **Deploy**: Docker, Kubernetes, Azure Container Apps, AWS ECS, Nginx
- **Monitoring**: Prometheus, structured logging

---

## Company

**Vidyuthlabs** — [vidyuthlabs.co.in](https://vidyuthlabs.co.in)
Product: **Parakram**
License: PolyForm Noncommercial 1.0.0
Target: 2M customers building IoT products in natural language
