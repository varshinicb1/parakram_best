# Contributing to Parakram

## Repository Structure

This is a monorepo. Each major component lives in its own directory:

- `android/` — Android app (Kotlin/Compose)
- `backend/` — Rust backend (axum)
- `firmware/` — ESP32 firmware (C, ESP-IDF)
- `desktop/` — Tauri desktop IDE + Python services
- `ios/` — iOS app (SwiftUI)

## Development Setup

### Backend
```bash
cd backend && cp .env.example .env && cargo run
```

### Desktop
```bash
cd desktop/services && pip install -r requirements.txt && python main.py
cd desktop/app && npm install && npm run dev
```

### Android
Open `android/` in Android Studio.

### Firmware
```bash
cd firmware && idf.py set-target esp32s3 && idf.py build
```

## Coding Standards

- **Rust**: `thiserror`, `tracing`, no `unwrap()` in prod
- **C (firmware)**: no `malloc` in VM, implement `driver_vtable_t`
- **Kotlin**: Compose, coroutines, Room
- **TypeScript**: React 19, Zustand, Tailwind
- **Python**: FastAPI, type hints, Pydantic

## Adding a New Driver

1. Add driver spec to `backend/src/drivers/registry.rs`
2. Update LLM prompt in `backend/src/llm/prompt.rs`
3. Implement C driver in `firmware/main/drivers/drv_<name>.c`
4. Add hardware JSON in `desktop/services/hardware_library/`
