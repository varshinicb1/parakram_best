# Parakram Unified — AI Agent Reference

Parakram is the core product of **Vidyuthlabs** (vidyuthlabs.co.in).
It is a zero-code embedded platform: users type plain English, and within ~500ms
the system generates, validates, and deploys executable bytecode to IoT hardware.

This is the **unified monorepo** combining all Parakram projects.

---

## What Actually Works Today

| Component | Status | Location |
|---|---|---|
| Rust backend (axum) | **Compiles + runs** (port 8400) | `backend/` |
| IR validation (8-step) | **Working** | `backend/src/ir/validator.rs` |
| Bytecode compiler | **Working** | `backend/src/compiler/` |
| Driver registry (59 specs) | **Working** | `backend/src/drivers/registry.rs` |
| LLM pipeline | **Working** | `backend/src/llm/` |
| JWT auth | **Working** | `backend/src/api/auth.rs` |
| Stripe billing | **Working** | `backend/src/billing/` |
| Driver marketplace | **Working** | `backend/src/marketplace/` |
| ROS 2 graph engine | **Working** | `backend/src/ros_graph/` |
| SQLite DB (9 tables, WAL) | **Working** | `backend/src/db/` |
| Web playground | **Working** | `playground/` |
| Admin panel | **Working** | `admin/` |
| Android app (BLE + AI) | **Working** | `android/` |
| Android app (billing/fleet) | **Working** | `android/vidyuthlabs-app/` |
| iOS app (SwiftUI) | **Working** | `ios/` |
| ESP32-S3 firmware (59 drivers) | **Builds** (needs idf.py) | `firmware/` |
| Multi-MCU HAL | **Complete** | `firmware/hal/` |
| Tauri desktop IDE (16 spaces) | **Working** | `desktop/app/` |
| Python FastAPI services | **Working** | `desktop/services/` |
| 202 golden blocks | **Working** | `desktop/services/agents/` |
| 150+ hardware lib JSONs | **Working** | `desktop/services/hardware_library/` |
| OTA firmware updates | **Working** | `firmware/main/ota_manager.c` |
| Cloud deployment | **Ready** | `deploy/` |
| CI/CD | **Ready** | `.github/workflows/` |
| RTOS kernel (experimental) | **Compiles** | `rtos/` |
| CodeLM spec | **Spec only** | `ai/codelm/` |

---

## Build & Run

### Backend
```bash
cd backend
cp .env.example .env
cargo run
```

### Desktop IDE
```bash
cd desktop/services && pip install -r requirements.txt && python main.py
cd desktop/app && npm install && npm run dev
```

### Tests
```bash
cd tests && bash integration_test.sh
```

### Docker
```bash
docker-compose up --build
```

---

## Key File Locations

| What | Where |
|---|---|
| LLM → IR pipeline | `backend/src/llm/` |
| IR schema & validator | `backend/src/ir/` |
| Bytecode compiler | `backend/src/compiler/` |
| Driver registry (59 specs) | `backend/src/drivers/registry.rs` |
| All backend API endpoints | `backend/src/api/` |
| Database schema | `backend/src/db/mod.rs` |
| Firmware boot sequence | `firmware/main/app_main.c` |
| Bytecode VM | `firmware/main/runtime/vm.c` |
| Firmware drivers (59) | `firmware/main/drivers/` |
| Multi-MCU PAL header | `firmware/hal/include/parakram_pal.h` |
| ESP32-S3 PAL impl | `firmware/hal/esp32s3/pal_impl.c` |
| RP2040 PAL impl | `firmware/hal/rp2040/pal_impl.c` |
| STM32F4 PAL impl | `firmware/hal/stm32/pal_impl.c` |
| Arduino PAL impl | `firmware/hal/arduino/pal_impl.cpp` |
| Android BLE manager | `android/app/src/.../hardware/TinkrBleManager.kt` |
| Android AI agent | `android/app/src/.../ai/TinkrAIService.kt` |
| Android protocol | `android/app/src/.../protocol/TinkrProtocol.kt` |
| iOS BLE manager | `ios/Parakram/BLE/BLEManager.swift` |
| Desktop Tauri app | `desktop/app/` |
| Desktop Python services | `desktop/services/` |
| Golden blocks (202) | `desktop/services/agents/golden_blocks*.py` |
| Hardware library (150+) | `desktop/services/hardware_library/` |
| Web playground | `playground/` |
| Admin panel | `admin/` |
| Kubernetes manifests | `deploy/kubernetes/` |
| OpenAPI spec | `shared/protocols/openapi.yaml` |
| RTOS kernel | `rtos/src/` |
| CodeLM spec | `ai/codelm/README.md` |

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

## Coding Standards

- Rust: use `thiserror` for errors, `tracing` for logs (not `println!`)
- Firmware C: no dynamic allocation in hot paths, no `malloc` in VM
- All new firmware drivers: implement `driver_vtable_t` from `driver_abi.h`
- All new backend drivers: add to both `registry.rs` AND `llm/prompt.rs`
- No `unwrap()` in production paths — use `?` or explicit error handling
- JWT auth required on all `/api/` endpoints except `/api/system/health`, `/api/drivers`, `/api/boards`

---

## Company

**Vidyuthlabs** — vidyuthlabs.co.in
Product: **Parakram**
License: PolyForm Noncommercial 1.0.0
