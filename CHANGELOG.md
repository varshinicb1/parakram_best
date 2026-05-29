# Changelog

All notable changes to the Parakram platform will be documented in this file.

This project adheres to [Semantic Versioning](https://semver.org/).

---

## [1.0.0] — 2026-05-29

### Summary

First production release of the Parakram unified platform — a zero-code IoT
system that translates natural language into executable bytecode for
microcontrollers. This release unifies the backend, firmware, desktop IDE,
mobile apps, AI model, and cloud deployment into a single monorepo.

### Backend (Rust/Axum)

- **69-driver registry** with full capability, bus, and address metadata
- **8-step IR validator** ensuring structural and semantic correctness
- **Ed25519 bytecode compiler** with constant-pool optimization and signing
- **V1 LLM intent pipeline** (`POST /api/llm/intent`) — natural language → IR → bytecode
- **V2 hallucination-proof pipeline** (`POST /api/llm/intent/v2`) — deterministic StructuredIntent builder with registry validation; eliminates LLM hallucination by design
- **NVIDIA NIM** as primary LLM provider (free tier), OpenRouter/Anthropic fallback
- **JWT authentication** on all protected endpoints
- **Stripe billing** integration with quota enforcement
- **Driver marketplace** with sandboxed community driver uploads
- **ROS 2 graph engine** for complex multi-device topologies
- **Secure provisioning** via X25519 key exchange (`/api/provisioning/`)
- **CodeLM bridge** API on port 8401
- **SQLite database** with WAL mode (9 tables)

### Firmware (ESP32-S3 / C)

- **69 hardware drivers** implementing `driver_vtable_t` ABI
- **Bytecode VM** executing signed IR payloads at runtime
- **Multi-MCU PAL** (Platform Abstraction Layer) supporting ESP32-S3, STM32F4, RP2040, Arduino
- **BLE E2E encryption** via `ble_crypto.c`
- **OTA firmware updates** via `ota_manager.c`
- **Lua scripting sandbox** for user-defined logic
- **UVC camera driver** for vision applications
- **DumbDisplay** protocol (TCP port 10201)
- **QEMU simulation** support with Wokwi config
- **Host test harness** — 8/8 VM unit tests passing on x86

### Desktop IDE (Tauri + React)

- **Parakram Studio** — zero-code visual IDE
- **248 golden blocks** — pre-verified, MISRA-compliant logic segments
- **Python sidecar services** (FastAPI) for hardware library management
- **TypeScript frontend** with Vite build system
- **Tauri v1/v2** shell for native desktop distribution

### Mobile Apps

- **Android** (Kotlin/Jetpack Compose)
  - BLE device management
  - AI agent (`TinkrAIService`)
  - DumbDisplay server (TCP 10201)
  - Vosk offline speech-to-text
  - Release signing configuration
- **iOS** (Swift/SwiftUI)
  - BLE hardware management
  - DumbDisplay client

### AI / CodeLM

- **Block-token transformer** for hardware-validated firmware synthesis
- Constraint head enforcing hardware compatibility
- Composition head for multi-block generation
- Corpus ingestion from 16 upstream repos
- Custom tokenizer for C function block-tokens
- 5 model tests + 3 corpus tests passing

### ROS 2

- **parakram_msgs** package — 7 message types + 3 service definitions
- Syntax-validated `.msg` and `.srv` files

### Cloud & DevOps

- **CI/CD** — GitHub Actions with 6 parallel jobs (backend, firmware VM, CodeLM, desktop, ROS 2, golden blocks)
- **Kubernetes** manifests for production deployment
- **AWS** and **Azure** deployment configs
- **Docker Compose** for local development

### Web

- **Playground** — browser-based IoT prototyping environment
- **Admin panel** — marketplace moderation and billing dashboard

### Experimental

- **parakram_os** (v0.1.0) — Rust-based RTOS kernel targeting Cortex-M and Xtensa

---

[1.0.0]: https://github.com/varshinicb1/parakram_best/releases/tag/v1.0.0
