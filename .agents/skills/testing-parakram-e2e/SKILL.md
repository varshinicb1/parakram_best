---
name: testing-parakram-e2e
description: End-to-end testing procedures for the Parakram unified stack (backend, firmware, golden blocks, Android app). Use when verifying PRs that touch drivers, golden blocks, backend registry, or firmware.
---

## Environment

- **Backend**: Rust/Axum on port 8400. Requires PostgreSQL (Supabase) via `SUPABASE_DB_URL` env var. Without DB credentials, the backend cannot start — use code-level verification for the driver registry instead (it's populated deterministically from Rust source, not from the database).
- **Firmware test harness**: `cd firmware/test_harness && make clean && make test` — compiles `vm.c` on host x86 with mock HAL. Expect 8/8 unit tests.
- **Android emulator**: Requires `ANDROID_HOME` to be set and an AVD configured. AVD name in previous sessions: `parakram_test` (Pixel 6, API 34, x86_64). If unavailable, test backend API via curl instead of app UI.
- **Backend build**: `cd backend && cargo build --release` — takes ~18 minutes cold (528 crates), <1 minute warm.

## Devin Secrets Needed

- `SUPABASE_DB_URL` — PostgreSQL connection string for backend startup
- `OPENROUTER_API_KEY` — LLM provider key (optional, only needed for LLM intent testing)

## Key Build & Test Commands

```bash
# Backend
cd backend && cargo build --release

# Firmware VM test harness (host x86)
cd firmware/test_harness && make clean && make test

# Validate ALL golden block JSONs across all categories
python3 -c "
import json, os, glob
files = glob.glob('desktop/services/hardware_library/**/*.json', recursive=True)
for f in files:
    try:
        d = json.load(open(f))
        print(f'{os.path.basename(f)}: OK')
    except Exception as e:
        print(f'{os.path.basename(f)}: FAIL ({e})')
print(f'Total: {len(files)} files')
"

# Count drivers in registry
grep -c 'self\.add(' backend/src/drivers/registry.rs

# Verify firmware drivers follow vtable ABI
grep -c 'driver_vtable_t\|driver_meta_t' firmware/main/drivers/drv_*.c

# Check capability enum duplicates
python3 -c "
import re
with open('firmware/main/include/driver_abi.h') as f:
    caps = re.findall(r'(CAP_\w+)\s*=\s*(\d+)', f.read())
vals = {}
for n,v in caps:
    v=int(v)
    if v in vals: print(f'DUPLICATE: {n}={v} vs {vals[v]}={v}')
    vals[v]=n
print(f'{len(caps)} enums, no duplicates' if len(vals)==len(caps) else 'DUPLICATES FOUND')
"

# Backend health check (when running)
curl -s http://localhost:8400/api/system/health | python3 -m json.tool

# List all drivers (when running)
curl -s http://localhost:8400/api/drivers | python3 -c "import json,sys; d=json.load(sys.stdin); print(f'Total: {d[\"total\"]}')"
```

## Testing Without Backend (No DB Credentials)

When PostgreSQL credentials are unavailable, verify the driver registry through code inspection:

1. **Driver count**: `grep -c 'self\.add(' backend/src/drivers/registry.rs` — compare with the comment near the `populate()` function
2. **Specific driver fields**: Parse `registry.rs` with python regex to extract version, type, capabilities for each driver
3. **LLM prompt sync**: Verify `backend/src/llm/prompt.rs` matches registry (driver count string, all driver names in correct sections)
4. **Backend compilation**: `cargo build --release` succeeding proves all type-level correctness

This is valid because the registry is an in-memory `HashMap` populated from source code constants, not from the database.

## Driver Type Values

Valid `driver_type` values in registry.rs (line 15):
- `"sensor"` — input-only devices (BME280, INMP441, I2C scanner, wake word, etc.)
- `"actuator"` — output-only devices (relay, servo, speaker, A2DP, etc.)
- `"display"` — display devices (DumbDisplay, SSD1306, ST7789, etc.)
- `"combo"` — devices that are both input and output (WiFi provisioning, BLE OTA, HTTP OTA, etc.)

Note: The LLM prompt groups drivers into sections (SENSORS, ACTUATORS, DISPLAYS, SYSTEM) that don't always map 1:1 to driver_type. For example, `"combo"` type drivers may appear in the "SYSTEM" prompt section. This is expected behavior, not a bug.

## Golden Block JSON Schema

Required fields for new golden blocks in `desktop/services/hardware_library/`:
- `id`, `name`, `category`, `description`
- `firmware_template.header` (C header)
- `firmware_template.source` (C implementation — must be >100 chars of real C code)
- `pins` (GPIO assignments)
- `verified: true`
- `anti_hallucination: true`

Additional checks for firmware_template.source quality:
- Must contain C keywords (void, int, #include, return, static, const)
- Must NOT contain "TODO", "FIXME", or "placeholder" (indicates incomplete implementation)
- If a golden block has placeholder code (e.g., TFLite inference stubs), flag it — the block won't work as advertised

Note: Pre-existing blocks (e.g. `audio_processor.json`, `esp32_manifest.json`) may lack some fields — don't flag these as failures from new PRs.

## S3-PRO PCB Pin Assignments

These are fixed by the PCB and must be consistent across all golden blocks:
- **INMP441 Mic**: WS=GPIO4, SCK=GPIO5, SD=GPIO7 (I2S_NUM_0)
- **MAX98357A/PAM8403 Speaker**: WS/LRC=GPIO15, BCK/BCLK=GPIO16, DOUT/DIN=GPIO17 (I2S_NUM_1)
- **DumbDisplay WiFi TCP**: Port 10201

## API Response Shapes

- `GET /api/drivers` → `{"drivers": [...], "total": N}`
- `GET /api/drivers/{name}` → single `DriverSpec` JSON object
- `GET /api/system/health` → `{"status": "ok", "database": "connected"|"disconnected", ...}`

## Common Issues

- **Backend exits immediately**: Usually missing `SUPABASE_DB_URL`. Check `.env` file exists in `backend/`.
- **Firmware test compile warnings**: Unused parameter warnings in `mock_subsystems.c` are expected and harmless.
- **Shell sluggishness during cargo build**: The 528-crate compilation is CPU-intensive. Run non-build tests in parallel, or expect <1s for warm builds.
- **`audio_processor.json` missing fields**: This is a pre-existing block, not part of new PRs. Don't report as a failure.
- **Pre-existing `QuotaError` unused import warning**: In `src/billing/mod.rs:15`. Pre-existing, harmless, does not indicate a regression.
- **`sqlx-postgres` future-incompat warning**: Informational only, does not affect build success.
