---
name: testing-parakram-e2e
description: End-to-end testing procedures for the Parakram unified stack (backend, firmware, golden blocks, Android app, CodeLM, Desktop IDE, ROS 2). Use when verifying PRs that touch drivers, golden blocks, backend registry, firmware, AI model, desktop frontend, or message types.
---

## Environment

- **Backend**: Rust/Axum on port 8400. Requires PostgreSQL (Supabase) via `SUPABASE_DB_URL` env var. Without DB credentials, the backend cannot start — use code-level verification for the driver registry instead (it's populated deterministically from Rust source, not from the database).
- **Firmware test harness**: `cd firmware/test_harness && make clean && make test` — compiles `vm.c` on host x86 with mock HAL. Expect 8/8 unit tests.
- **Android emulator**: Requires `ANDROID_HOME` to be set and an AVD configured. AVD name in previous sessions: `parakram_test` (Pixel 6, API 34, x86_64). If unavailable, test backend API via curl instead of app UI.
- **Backend build**: `cd backend && cargo build --release` — takes ~18 minutes cold (528 crates), <1 minute warm.
- **CodeLM tests**: Requires PyTorch CPU (`pip3 install torch --index-url https://download.pytorch.org/whl/cpu`), pytest, numpy, sqlalchemy. Run: `cd ai/codelm && PYTHONPATH=. python3 -m pytest tests/ -v`
- **Desktop IDE**: Requires Node.js + npm. Setup: `cd desktop && npm install`. TypeScript check: `cd desktop && npx tsc --noEmit`. Dev server: `cd desktop && npm run dev` (Vite on port 5173).
- **ROS 2 messages**: Files in `ros2_ws/src/parakram_msgs/`. No ROS 2 installation needed for syntax validation — use Python script. Full compilation requires `colcon build` in a ROS 2 workspace.

## Devin Secrets Needed

- `SUPABASE_DB_URL` — PostgreSQL connection string for backend startup
- `OPENROUTER_API_KEY` — LLM provider key (optional, only needed for LLM intent testing)

## Key Build & Test Commands

```bash
# Backend
cd backend && cargo build --release

# Firmware VM test harness (host x86)
cd firmware/test_harness && make clean && make test

# CodeLM model tests (5 tests: forward pass, param count, tokenizer, constraint head, composition head)
cd ai/codelm && PYTHONPATH=. python3 -m pytest tests/test_model.py -v

# CodeLM corpus tests (3 tests: source definitions, extractor regex, tag inference)
cd ai/codelm && PYTHONPATH=. python3 -m pytest tests/test_corpus.py -v

# Desktop IDE TypeScript check
cd desktop && npx tsc --noEmit

# Desktop IDE dev server
cd desktop && npm run dev

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

# ROS 2 message syntax validation (no ROS 2 installation needed)
python3 -c "
import os
for d, ext in [('ros2_ws/src/parakram_msgs/msg', '.msg'), ('ros2_ws/src/parakram_msgs/srv', '.srv')]:
    files = [f for f in os.listdir(d) if f.endswith(ext)]
    for f in files:
        content = open(os.path.join(d, f)).read().strip()
        lines = [l for l in content.split('\\n') if l.strip() and not l.strip().startswith('#')]
        if ext == '.srv' and '---' not in content:
            print(f'{f}: FAIL (missing --- separator)')
        else:
            print(f'{f}: {len(lines)} lines - OK')
    print(f'{len(files)} {ext} files')
"

# Provisioning API code verification (no live backend needed)
python3 -c "
with open('backend/src/api/provisioning.rs') as f:
    c = f.read()
for fn in ['key_exchange', 'get_session', 'delete_session']:
    print(f'{fn}: {\"found\" if f\"pub async fn {fn}\" in c else \"MISSING\"}')  
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
5. **Provisioning API**: Code inspection of `src/api/provisioning.rs` — verify handler functions, request/response types, route wiring in `mod.rs`

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
- `POST /api/provisioning/key-exchange` → `KeyExchangeResponse` JSON
- `GET /api/provisioning/session/:device_id` → session details
- `DELETE /api/provisioning/session/:device_id` → 200 OK

## CodeLM Test Details

The CodeLM tests verify the block-token transformer architecture:
- **test_model_forward_pass**: Creates model with vocab_size=1024, batch=2, seq_len=16. Output must be `(2, 16, 1024)`.
- **test_model_parameter_count**: Total params must be between 1M and 200M (fits 6GB VRAM).
- **test_tokenizer_roundtrip**: Encode `["block_gpio_init", "block_spi_transfer", "block_i2c_read"]` → decode must return identical list.
- **test_constraint_head**: Output shape `(2, 4)`, all values in [0, 1] (sigmoid).
- **test_composition_head**: Output shape `(2, K)` where K = number of candidates.
- **test_source_definitions**: All 16 upstream repos have name, URL (https), ref, tier (1-3), license.
- **test_extractor_regex**: C function extraction regex matches ≥ 2 functions from test code.
- **test_tag_inference**: Peripheral tags correctly inferred from function names/bodies.

## Common Issues

- **Backend exits immediately**: Usually missing `SUPABASE_DB_URL`. Check `.env` file exists in `backend/`.
- **Firmware test compile warnings**: Unused parameter warnings in `mock_subsystems.c` are expected and harmless.
- **Shell sluggishness during cargo build**: The 528-crate compilation is CPU-intensive. Run non-build tests in parallel, or expect <1s for warm builds.
- **`audio_processor.json` missing fields**: This is a pre-existing block, not part of new PRs. Don't report as a failure.
- **Pre-existing `QuotaError` unused import warning**: In `src/billing/mod.rs:15`. Pre-existing, harmless, does not indicate a regression.
- **`sqlx-postgres` future-incompat warning**: Informational only, does not affect build success.
- **Desktop IDE TS errors after Tauri API changes**: `invoke()` returns `Promise<unknown>`, not typed. Use `unknown` + runtime narrowing in `.then()` callbacks.
- **CodeLM tests need PYTHONPATH**: Run with `PYTHONPATH=.` or `PYTHONPATH=/path/to/ai/codelm` to resolve imports.
