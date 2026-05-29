# parakram_best

**The unified Parakram platform** — Phone as Brain + Factory Firmware as Body.

This repository contains the complete vision, migration plan, and tooling to build the next-generation Parakram experience.

## Repository Structure

```
parakram_best/
├── README.md
├── PARAKRAM_UNIFIED_VISION_AND_MIGRATION_PLAN.md   # Main blueprint
├── docs/
│   └── agents.md                                    # Instructions for AI agents
├── scripts/
│   └── clone_oss_deps.sh                            # Clone all required OSS repos
└── firmware/                                        # (To be created) Factory Firmware
    └── deps/                                        # OSS dependencies (run the script here)
```

## Quick Start

1. **Clone the OSS dependencies** (recommended first step):
   ```bash
   mkdir -p firmware/deps
   cd firmware/deps
   bash ../../scripts/clone_oss_deps.sh
   ```

2. **To update existing dependencies later**:
   ```bash
   cd firmware/deps
   bash ../../scripts/clone_oss_deps.sh --update
   ```

3. Read the main plan:
   ```bash
   cat PARAKRAM_UNIFIED_VISION_AND_MIGRATION_PLAN.md
   ```

## Key Documents

- **`PARAKRAM_UNIFIED_VISION_AND_MIGRATION_PLAN.md`** — Complete vision + migration strategy
- **`docs/agents.md`** — Strict operating instructions for any AI working on this repo

## Vision

Turn the existing Parakram Android app into a complete **phone-brained embedded platform** by building a smart Factory Firmware for the ESP32-S3 that makes hardware peripherals "just work" with zero low-level driver code from the user.

---

**Status**: Planning & Architecture Phase

Ready to build the future of accessible physical computing.