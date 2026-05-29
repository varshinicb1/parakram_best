---
name: testing-parakram-e2e
description: End-to-end testing procedures for the Parakram unified stack (backend, firmware, golden blocks, Android app). Use when verifying PRs that touch drivers, golden blocks, backend registry, or firmware.
---

## Environment

- **Backend**: Rust/Axum on port 8400. Requires PostgreSQL (Supabase) via `SUPABASE_DB_URL` env var. Without DB credentials, the backend cannot start — use code-level verification for the driver registry instead (it's populated deterministically from Rust source, not from the database).
- **Firmware test harness**: `cd firmware/test_harness && make clean && make test` — compiles `vm.c` on host x86 with mock HAL. Expect 8/8 unit tests.
- **Android emulator**: Requires `ANDROID_HOME` to be set and an AVD configured. AVD name in previous sessions: `parakram_test` (Pixel 6, API 34, x86_64). If unavailable, test backend API via curl instead of app UI.
- **Backend build**: `cd backend && cargo build --release` — takes ~18 minutes cold, compiles 528 crates.

## Devin Secrets Needed

- `SUPABASE_DB_URL` — PostgreSQL connection string for backend startup
- `OPENROUTER_API_KEY` — LLM provider key (optional, only needed for LLM intent testing)

## Key Build & Test Commands

```bash
# Backend
cd backend && cargo build --release

# Firmware VM test harness (host x86)
cd firmware/test_harness && make clean && make test

# Validate golden block JSONs
cd desktop/services/hardware_library/audio
python3 -c "import json, os; [json.load(open(f)) for f in os.listdir('.') if f.endswith('.json')]"

# Count drivers in registry
grep -c 'self\.add(' backend/src/drivers/registry.rs

# Backend health check (when running)
curl -s http://localhost:8400/api/system/health | python3 -m json.tool

# List all drivers (when running)
curl -s http://localhost:8400/api/drivers | python3 -c "import json,sys; d=json.load(sys.stdin); print(f'Total: {d[\"total\"]}'); [print(f'  {x[\"name\"]} v{x[\"version\"]} ({x[\"driver_type\"]})') for x in d[\"drivers\"] if \"audio\" in str(x.get(\"capabilities\",[])) or \"audio\" in x.get(\"name\",\"\")]"
```

## Testing Without Backend (No DB Credentials)

When PostgreSQL credentials are unavailable, verify the driver registry through code inspection:

1. **Driver count**: `grep -c 'self\.add(' backend/src/drivers/registry.rs` — compare with comment on line ~65
2. **Specific driver fields**: Parse `registry.rs` with python regex to extract version, type, capabilities for each driver
3. **LLM prompt sync**: Verify `backend/src/llm/prompt.rs` matches registry (driver count, capability strings)
4. **Backend compilation**: `cargo build --release` succeeding proves all type-level correctness

This is valid because the registry is an in-memory `HashMap` populated from source code constants, not from the database.

## Golden Block JSON Schema

Required fields for new golden blocks in `desktop/services/hardware_library/`:
- `id`, `name`, `category`, `description`
- `firmware_template.header` (C header)
- `firmware_template.source` (C implementation)
- `pins` (GPIO assignments)
- `verified: true`
- `anti_hallucination: true`

Note: Pre-existing blocks (e.g. `audio_processor.json`) may lack some fields — don't flag these as failures.

## S3-PRO PCB Pin Assignments

These are fixed by the PCB and must be consistent across all golden blocks:
- **INMP441 Mic**: WS=GPIO4, SCK=GPIO5, SD=GPIO7 (I2S_NUM_0)
- **MAX98357A/PAM8403 Speaker**: WS/LRC=GPIO15, BCK/BCLK=GPIO16, DOUT/DIN=GPIO17 (I2S_NUM_1)

## API Response Shapes

- `GET /api/drivers` → `{"drivers": [...], "total": N}`
- `GET /api/drivers/{name}` → single `DriverSpec` JSON object
- `GET /api/system/health` → `{"status": "ok", "database": "connected"|"disconnected", ...}`

## Common Issues

- **Backend exits immediately**: Usually missing `SUPABASE_DB_URL`. Check `.env` file exists in `backend/`.
- **Firmware test compile warnings**: Unused parameter warnings in `mock_subsystems.c` are expected and harmless.
- **Shell sluggishness during cargo build**: The 528-crate compilation is CPU-intensive. Run non-build tests in parallel or wait for build to complete.
- **`audio_processor.json` missing fields**: This is a pre-existing block, not part of new PRs. Don't report as a failure.
