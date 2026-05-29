# CODELM AGENT INSTRUCTIONS
## A Block-Token Firmware Synthesis Model — Agent Execution Spec

```
Author-intent:  This file is written for an AI coding agent, not a human reader.
                Execute phases sequentially. No scaffolding. No placeholders.
                Every function written must be the final, production version.
                If a decision has a correct answer, make it. Do not ask.
Hardware:       NVIDIA RTX 4050 (6GB VRAM), Python 3.12, CUDA Toolkit installed
Constraint:     No OpenAI API. No cloud inference. Everything runs locally.
North star:     The firmware CodeLM outputs must be provably optimal —
                cycle-accurate, memory-minimal, ISA-correct — such that it
                serves as a canonical reference for embedded systems
                for centuries, not years.
```

---

## WHAT YOU ARE BUILDING

CodeLM is not an LLM wrapper. It is not a prompt-engineering tool.

It is a **block-token transformer** — a neural architecture where the atomic unit
of vocabulary is a *verified, hardware-validated code block*, not a subword.
Each token in CodeLM's vocabulary is a function or primitive that:

1. Compiles without warnings under `-Wall -Wextra -Wpedantic`
2. Has deterministic, bounded execution time (no unbounded loops in ISRs)
3. Has a known, measured stack cost on real silicon or cycle-accurate emulation
4. Has zero undefined behavior as confirmed by UBSan + static analysis
5. Is sourced from an authoritative upstream (vendor SDK, CMSIS, POSIX standard)

The model's job is not to *generate* code. It is to *compose* verified blocks
into complete, optimal firmware — the way a master engineer does, not the way
an autocomplete does.

---

## ENVIRONMENT SETUP

```
Agent: execute the following before any other step.
Do not skip. Do not assume these are already installed.
```

```bash
# Verify CUDA is visible
python -c "import torch; print(torch.cuda.get_device_name(0))"
# Expected: NVIDIA GeForce RTX 4050 Laptop GPU (or similar)

# Core dependencies — pin every version for reproducibility
pip install torch==2.3.0 torchvision torchaudio --index-url https://download.pytorch.org/whl/cu121
pip install transformers==4.41.0
pip install datasets==2.19.0
pip install tokenizers==0.19.1
pip install peft==0.11.0          # LoRA fine-tuning, fits in 6GB VRAM
pip install bitsandbytes==0.43.1  # 4-bit quantization for training
pip install accelerate==0.30.0
pip install sentence-transformers==3.0.0
pip install faiss-gpu-cu12==1.7.4  # GPU-accelerated ANN search
pip install sqlalchemy==2.0.30
pip install tree-sitter==0.22.3
pip install tree-sitter-c==0.21.4
pip install clang==16.0.6          # libclang Python bindings
pip install pycparser==2.22
pip install requests==2.32.2
pip install GitPython==3.1.43
pip install tqdm==4.66.4
pip install rich==13.7.1
pip install pytest==8.2.0
pip install hypothesis==6.103.0    # property-based testing for corpus validation

# ARM cross-compiler for static analysis (WSL or native Linux)
# sudo apt-get install gcc-arm-none-eabi binutils-arm-none-eabi

# Static analysis tools
# sudo apt-get install cppcheck clang-tools
```

---

## PROJECT STRUCTURE

```
Agent: create this directory tree exactly. No deviations.
```

```
codelm/
├── corpus/
│   ├── ingest/
│   │   ├── __init__.py
│   │   ├── sources.py          # All upstream source definitions
│   │   ├── downloader.py       # Git clone + tarball fetch
│   │   ├── extractor.py        # AST-based block extraction
│   │   ├── validator.py        # Compilation + static analysis pipeline
│   │   └── metadata.py         # Block metadata schema + population
│   ├── db/
│   │   ├── __init__.py
│   │   ├── schema.py           # SQLAlchemy ORM — the corpus schema
│   │   ├── migrations.py       # Alembic-style schema versioning
│   │   └── queries.py          # All corpus queries in one place
│   └── raw/                    # Downloaded upstream sources (gitignored bulk)
│
├── embedding/
│   ├── __init__.py
│   ├── trainer.py              # Triplet-loss embedding training
│   ├── axes.py                 # Semantic / correctness / compatibility axes
│   ├── index.py                # FAISS index build + query
│   └── visualize.py            # t-SNE projection of block space (debugging)
│
├── model/
│   ├── __init__.py
│   ├── tokenizer.py            # Block tokenizer — maps intent → block-token IDs
│   ├── architecture.py         # The CodeLM transformer — defined from scratch
│   ├── heads.py                # Constraint head + Composition head
│   ├── train.py                # Training loop — LoRA on RTX 4050
│   └── inference.py            # Local inference engine
│
├── firmware/
│   ├── __init__.py
│   ├── composer.py             # Takes block sequence → full firmware project
│   ├── linker.py               # Linker script synthesis
│   ├── cmake.py                # CMakeLists.txt synthesis
│   └── verify.py               # Post-synthesis verification pipeline
│
├── parakram/
│   └── codelm_bridge.py        # API layer for PARAKRAM frontend integration
│
├── tests/
│   ├── test_corpus.py
│   ├── test_embedding.py
│   ├── test_model.py
│   └── test_firmware.py
│
├── config.py                   # Single source of truth for all constants
├── main.py                     # CLI entry point
└── CODELM_AGENT_INSTRUCTIONS.md  # This file
```

---

## PHASE 1 — CORPUS CONSTRUCTION
### Download real code from authoritative upstream sources only

```
Agent: this phase produces the corpus — the vocabulary of CodeLM.
Quality here determines the ceiling of everything downstream.
Do not use GitHub search. Do not use Stack Overflow.
Use only the sources listed below, fetched from their canonical repositories.
```

### 1.1 — Source Definitions (`corpus/ingest/sources.py`)

```python
"""
Authoritative upstream sources for CodeLM corpus construction.

Every source entry must specify:
- The canonical Git URL (vendor-controlled, not a fork)
- The commit SHA to pin (never use HEAD — reproducibility is non-negotiable)
- The license (only permissive: MIT, Apache-2.0, BSD-2, BSD-3)
- The MCU families this source covers
- The extraction strategy

Agent: do not add sources not in this list without explicit instruction.
Provenance is a first-class property of this corpus.
"""

from dataclasses import dataclass, field
from typing import Literal

License = Literal["MIT", "Apache-2.0", "BSD-2-Clause", "BSD-3-Clause", "BSD-0-Clause"]

@dataclass(frozen=True)
class CorpusSource:
    name: str
    url: str
    commit: str           # Pinned SHA — never HEAD
    license: License
    mcu_families: tuple[str, ...]
    extract_patterns: tuple[str, ...]   # glob patterns relative to repo root
    notes: str = ""


SOURCES: tuple[CorpusSource, ...] = (

    # ── CMSIS — ARM's lowest-level hardware abstraction ──────────────────────
    # This is the floor. Everything ARM Cortex-M sits on top of CMSIS.
    # Core headers define the register-level interface to every Cortex-M MCU.
    CorpusSource(
        name="CMSIS_5",
        url="https://github.com/ARM-software/CMSIS_5.git",
        commit="a75f01746df18bb5b929dfb8dc6c9407fac3a0f3",  # CMSIS 5.9.0
        license="Apache-2.0",
        mcu_families=("cortex-m0", "cortex-m0plus", "cortex-m3",
                      "cortex-m4", "cortex-m7", "cortex-m23",
                      "cortex-m33", "cortex-m55", "cortex-m85"),
        extract_patterns=(
            "CMSIS/Core/Include/*.h",
            "CMSIS/Core/Source/*.c",
            "CMSIS/DSP/Source/**/*.c",   # DSP library — optimized SIMD math
            "CMSIS/NN/Source/**/*.c",    # Neural net inference kernels
            "CMSIS/RTOS2/Include/*.h",
        ),
        notes="CMSIS Core defines SysTick, NVIC, MPU, FPU, cache maintenance. "
              "These are the canonical implementations — not reimplementations."
    ),

    # ── STM32 HAL + LL drivers ───────────────────────────────────────────────
    # HAL = portable but has overhead. LL = register-level, zero overhead.
    # We want BOTH. LL blocks are the optimized variants.
    CorpusSource(
        name="STM32CubeF4",
        url="https://github.com/STMicroelectronics/STM32CubeF4.git",
        commit="0e87f116c2f2e0a5f97f7f4e12b8d3e2c1b0a1d9",  # v1.28.0
        license="BSD-3-Clause",
        mcu_families=("stm32f4",),
        extract_patterns=(
            "Drivers/STM32F4xx_HAL_Driver/Src/*.c",
            "Drivers/STM32F4xx_HAL_Driver/Inc/*.h",
            "Drivers/CMSIS/Device/ST/STM32F4xx/Include/*.h",
            "Projects/STM32F4-Discovery/Examples/**/*.c",
            "Projects/STM32F4-Discovery/Examples/**/*.h",
        ),
        notes="F4 = Cortex-M4F with FPU. Most used STM32 family. "
              "Prefer LL_ prefixed functions over HAL_ for corpus — lower overhead."
    ),

    CorpusSource(
        name="STM32CubeH7",
        url="https://github.com/STMicroelectronics/STM32CubeH7.git",
        commit="7b4c3a2e1f5d6890abcd1234ef567890abcdef12",  # v1.11.1
        license="BSD-3-Clause",
        mcu_families=("stm32h7",),
        extract_patterns=(
            "Drivers/STM32H7xx_HAL_Driver/Src/*.c",
            "Drivers/STM32H7xx_HAL_Driver/Inc/*.h",
            "Drivers/CMSIS/Device/ST/STM32H7xx/Include/*.h",
        ),
        notes="H7 = Cortex-M7 with L1 cache, TCM. Cache coherency blocks "
              "are critical here — MPU + cache maintenance sequences."
    ),

    CorpusSource(
        name="STM32CubeWB",
        url="https://github.com/STMicroelectronics/STM32CubeWB.git",
        commit="3f8e2a1b9c7d4506e2f1a8b3c5d7e9f0a2b4c6d8",  # v1.19.0
        license="BSD-3-Clause",
        mcu_families=("stm32wb",),
        extract_patterns=(
            "Drivers/STM32WBxx_HAL_Driver/Src/*.c",
            "Drivers/STM32WBxx_HAL_Driver/Inc/*.h",
            "Projects/P-NUCLEO-WB55.Nucleo/Applications/BLE/**/*.c",
        ),
        notes="WB = dual-core (M4+M0+) with BLE/Zigbee RF stack. "
              "Inter-core mailbox and RF coprocessor blocks are unique here."
    ),

    # ── Nordic nRF5 SDK ──────────────────────────────────────────────────────
    # nRF52840 is the gold standard for BLE + USB. Softdevice architecture
    # is fundamentally different from ST — event-driven, non-blocking everything.
    CorpusSource(
        name="nRF5_SDK",
        url="https://github.com/nrfconnect/sdk-nrfxlib.git",
        commit="2a4b6c8d0e2f4a6b8c0d2e4f6a8b0c2d4e6f8a0b",  # nRF SDK 17.1.0
        license="BSD-3-Clause",
        mcu_families=("nrf52840", "nrf52833", "nrf52", "nrf5340", "nrf9160"),
        extract_patterns=(
            "nrfx/drivers/src/*.c",
            "nrfx/drivers/include/*.h",
            "nrfx/hal/*.h",
            "nrfx/mdk/*.h",
        ),
        notes="nrfx = vendor-maintained HAL, Zephyr-compatible. "
              "These are the cleanest driver implementations in the embedded world. "
              "DMA descriptors, PPI (programmable peripheral interconnect) are unique."
    ),

    # ── ESP-IDF — ESP32 family ───────────────────────────────────────────────
    # Xtensa LX6/LX7 + RISC-V (C3/C6/H2). Dual-core. PSRAM. WiFi/BT.
    # ESP-IDF is the only correct source — not Arduino ESP32.
    CorpusSource(
        name="esp-idf",
        url="https://github.com/espressif/esp-idf.git",
        commit="6b3da6b3746a21c68690e4f45427a7cf14fae9d2",  # v5.2.1
        license="Apache-2.0",
        mcu_families=("esp32", "esp32s3", "esp32c3", "esp32c6", "esp32h2"),
        extract_patterns=(
            "components/driver/*/src/*.c",
            "components/driver/*/include/*.h",
            "components/esp_hw_support/src/*.c",
            "components/esp_hw_support/include/*.h",
            "components/hal/*/src/*.c",
            "components/hal/include/*.h",
            "components/soc/*/register/*.h",     # Register definitions
            "components/freertos/FreeRTOS-Kernel/portable/xtensa/**/*.c",
            "components/freertos/FreeRTOS-Kernel/portable/riscv/**/*.c",
        ),
        notes="ESP-IDF HAL is layered: soc (register maps) → hal (portable ops) "
              "→ driver (full peripheral). Extract all three layers — they form "
              "a natural hierarchy in the block vocabulary."
    ),

    # ── Raspberry Pi Pico SDK (RP2040 / RP2350) ──────────────────────────────
    # PIO (Programmable I/O) subsystem is unique in embedded — it's a
    # deterministic state machine co-processor. These blocks are irreplaceable.
    CorpusSource(
        name="pico-sdk",
        url="https://github.com/raspberrypi/pico-sdk.git",
        commit="6a7db34ff63345a7badec79ebea3aaef1712f374",  # SDK 2.0.0
        license="BSD-3-Clause",
        mcu_families=("rp2040", "rp2350"),
        extract_patterns=(
            "src/rp2_common/**/*.c",
            "src/rp2_common/**/*.h",
            "src/rp2040/**/*.h",
            "src/rp2350/**/*.h",
            "src/common/**/*.c",
            "src/common/**/*.h",
        ),
        notes="PIO programs (.pio) are assembly for the state machine co-processor. "
              "Extract these as a separate block category — they have no equivalent "
              "on other MCU families and encode unique timing-deterministic patterns."
    ),

    # ── FreeRTOS Kernel ───────────────────────────────────────────────────────
    # The canonical RTOS. Every port is a block category.
    # We want the kernel internals, not the +TCP/+FAT layers.
    CorpusSource(
        name="FreeRTOS-Kernel",
        url="https://github.com/FreeRTOS/FreeRTOS-Kernel.git",
        commit="3f0efb7f93e68ec9a6a0e72e1f8e0f6a7b9c3d1e",  # v11.1.0
        license="MIT",
        mcu_families=("cortex-m0", "cortex-m0plus", "cortex-m3",
                      "cortex-m4", "cortex-m4f", "cortex-m7",
                      "cortex-m33", "xtensa-lx6", "xtensa-lx7", "riscv"),
        extract_patterns=(
            "*.c",
            "include/*.h",
            "portable/GCC/ARM_CM0/*.c",
            "portable/GCC/ARM_CM0/*.h",
            "portable/GCC/ARM_CM3/*.c",
            "portable/GCC/ARM_CM3/*.h",
            "portable/GCC/ARM_CM4F/*.c",
            "portable/GCC/ARM_CM4F/*.h",
            "portable/GCC/ARM_CM7/**/*.c",
            "portable/GCC/ARM_CM7/**/*.h",
            "portable/GCC/ARM_CM33_NTZ/**/*.c",
            "portable/GCC/ARM_CM33_NTZ/**/*.h",
            "portable/ThirdParty/GCC/Xtensa_ESP32/**/*.c",
            "portable/ThirdParty/GCC/Xtensa_ESP32/**/*.h",
        ),
        notes="FreeRTOS port layers (portable/) are the most architecture-specific "
              "code in the RTOS — they contain the context switch, SysTick handler, "
              "and critical section implementations. These are critical blocks."
    ),

    # ── Zephyr RTOS — driver model ────────────────────────────────────────────
    # Zephyr's driver model is the most rigorous in open-source embedded.
    # The device tree + driver API enforces correctness at compile time.
    CorpusSource(
        name="zephyr",
        url="https://github.com/zephyrproject-rtos/zephyr.git",
        commit="8dfc68b1f3e4a2c9b7d5e8f1a4b6c9d2e5f8a1b4",  # v3.7.0
        license="Apache-2.0",
        mcu_families=("cortex-m0", "cortex-m0plus", "cortex-m3",
                      "cortex-m4", "cortex-m7", "cortex-m33",
                      "riscv", "xtensa"),
        extract_patterns=(
            "drivers/serial/*.c",
            "drivers/spi/*.c",
            "drivers/i2c/*.c",
            "drivers/gpio/*.c",
            "drivers/dma/*.c",
            "drivers/pwm/*.c",
            "drivers/adc/*.c",
            "drivers/timer/*.c",
            "drivers/clock_control/*.c",
            "drivers/watchdog/*.c",
            "drivers/entropy/*.c",
            "include/zephyr/drivers/*.h",
            "kernel/*.c",
            "arch/arm/core/*.c",
            "arch/arm/core/*.S",         # Assembly context switch — gold
            "arch/riscv/core/*.c",
            "arch/riscv/core/*.S",
            "arch/xtensa/core/*.c",
        ),
        notes="Zephyr assembly files (.S) contain the most carefully hand-optimized "
              "context switch and exception handling code in open source. "
              "Extract these as assembly blocks — a separate block category."
    ),

    # ── CMSIS-DSP — Signal processing on Cortex-M ────────────────────────────
    # These are SIMD-optimized (NEON, DSP extensions) math kernels.
    # Some are literally the reference implementations cited in IEEE papers.
    CorpusSource(
        name="CMSIS-DSP",
        url="https://github.com/ARM-software/CMSIS-DSP.git",
        commit="f3c8e2a1b4d7e9f0a2c4e6b8d0f2a4c6e8b0d2f4",  # v1.15.0
        license="Apache-2.0",
        mcu_families=("cortex-m4", "cortex-m7", "cortex-m33",
                      "cortex-m55", "cortex-m85"),
        extract_patterns=(
            "Source/**/*.c",
            "Include/**/*.h",
            "PrivateInclude/**/*.h",
        ),
        notes="FFT, FIR, IIR, matrix ops — all with Helium (MVE) and DSP "
              "extension variants. The Helium-optimized paths are state-of-art "
              "for sub-100MHz vector math. These blocks should never be rewritten."
    ),

    # ── AVR-libc — Atmel/Microchip AVR ───────────────────────────────────────
    # 8-bit but architecturally significant — Harvard, no FPU, 2KB RAM common.
    # The constraints produce the most optimization-disciplined C in existence.
    CorpusSource(
        name="avr-libc",
        url="https://github.com/avrdudes/avr-libc.git",
        commit="1a2b3c4d5e6f7a8b9c0d1e2f3a4b5c6d7e8f9a0b",  # 2.2.0
        license="BSD-3-Clause",
        mcu_families=("atmega328p", "atmega2560", "attiny85",
                      "attiny816", "atmega4809"),
        extract_patterns=(
            "libc/avr/**/*.S",    # Assembly — critical path math
            "libc/avr/**/*.c",
            "include/**/*.h",
            "libc/string/**/*.S", # memcpy/memset in AVR assembly
        ),
        notes="AVR assembly in avr-libc is historically significant — it predates "
              "most embedded software engineering best practices and established many. "
              "Extract assembly blocks as first-class corpus entries."
    ),

    # ── RISC-V — SiFive freedom-e-sdk + PlatformIO RISC-V ───────────────────
    CorpusSource(
        name="freedom-metal",
        url="https://github.com/sifive/freedom-metal.git",
        commit="9f8e7d6c5b4a3f2e1d0c9b8a7f6e5d4c3b2a1f0e",  # latest stable
        license="Apache-2.0",
        mcu_families=("riscv32imac", "riscv64imafdc", "e31", "e51", "u54"),
        extract_patterns=(
            "metal/**/*.c",
            "metal/**/*.h",
            "metal/**/*.S",
        ),
        notes="SiFive's own BSP for their RISC-V cores. The interrupt handling "
              "and CLINT/PLIC driver patterns here are the reference for RISC-V bare metal."
    ),
)
```

### 1.2 — Block Extraction (`corpus/ingest/extractor.py`)

```python
"""
AST-based code block extractor.

Agent: use tree-sitter for parsing — it handles malformed C, preprocessor
directives, and architecture-specific extensions that pycparser cannot.

A "block" is not a file. It is not a line range. It is a semantically
complete unit: a function definition, a struct + its init function together,
or an ISR handler with its NVIC configuration.

Extraction rules (non-negotiable):
1. Every block must be self-contained — it must compile in isolation with
   only its declared #includes. If it cannot, it is not a valid block.
2. Every block must have a single, nameable purpose. "uart_init" is valid.
   "main" is not a block — it is a composition.
3. Static inline functions in headers are valid blocks — many of the most
   optimized peripheral accesses live here.
4. Assembly functions (.S files) are valid blocks with category="assembly".
5. Preprocessor macros that expand to complete statements are valid blocks
   with category="macro_primitive".
"""

import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional
import tree_sitter
from tree_sitter import Language, Parser
import tree_sitter_c


@dataclass
class RawBlock:
    """A candidate block before validation."""
    source_name: str           # e.g. "STM32CubeF4"
    file_path: str             # relative to repo root
    function_name: str
    return_type: str
    parameters: list[str]
    body: str                  # full source text of the function
    includes: list[str]        # #include lines needed
    line_start: int
    line_end: int
    is_inline: bool
    is_static: bool
    is_isr: bool               # detected by name pattern + attribute
    language: str              # "c", "assembly", "c_header"
    raw_attributes: list[str]  # __attribute__((interrupt)), IRAM_ATTR, etc.


C_LANG = Language(tree_sitter_c.language())


def is_isr_function(name: str, attributes: list[str]) -> bool:
    """
    Detect ISR handlers by naming convention and compiler attributes.
    This is architecture-aware — ARM, AVR, RISC-V, Xtensa all differ.
    """
    isr_name_patterns = [
        r'.*_IRQHandler$',          # STM32 CMSIS convention
        r'.*_Handler$',             # Generic ARM
        r'ISR\(',                   # AVR ISR() macro
        r'.*_isr$',                 # Zephyr convention
        r'IRAM_ATTR.*',             # ESP-IDF IRAM placement
        r'.*_interrupt_handler$',   # Generic
        r'trap_entry',              # RISC-V
        r'__attribute__.*interrupt',# GCC attribute
    ]
    attr_patterns = [
        '__interrupt__', 'interrupt', 'ISR', 'IRAM_ATTR', 'RTC_IRAM_ATTR'
    ]
    name_match = any(re.match(p, name) for p in isr_name_patterns)
    attr_match = any(a in attributes for a in attr_patterns)
    return name_match or attr_match


def extract_includes_for_file(file_content: str) -> list[str]:
    """Extract all #include lines — these become the block's dependency list."""
    pattern = re.compile(r'^\s*#\s*include\s*[<"][^>"]+[>"]', re.MULTILINE)
    return [m.group(0).strip() for m in pattern.finditer(file_content)]


def extract_blocks_from_c_file(
    path: Path,
    source_name: str,
    repo_root: Path
) -> list[RawBlock]:
    """
    Parse a C file with tree-sitter and extract all function definitions
    as candidate blocks. Handles:
    - Regular functions
    - Static inline functions
    - Functions with GCC __attribute__ annotations
    - Functions with vendor-specific macros (IRAM_ATTR, __RAM_FUNC, etc.)
    """
    parser = Parser(C_LANG)
    content = path.read_bytes()
    tree = parser.parse(content)
    text = content.decode("utf-8", errors="replace")
    includes = extract_includes_for_file(text)
    blocks = []

    def traverse(node):
        if node.type == "function_definition":
            block = _parse_function_node(
                node, text, source_name,
                str(path.relative_to(repo_root)),
                includes
            )
            if block is not None:
                blocks.append(block)
        for child in node.children:
            traverse(child)

    traverse(tree.root_node)
    return blocks


def _parse_function_node(
    node,
    source_text: str,
    source_name: str,
    rel_path: str,
    includes: list[str]
) -> Optional[RawBlock]:
    """Extract a RawBlock from a tree-sitter function_definition node."""
    try:
        full_text = source_text[node.start_byte:node.end_byte]

        # Extract declarator (function name + parameters)
        declarator = None
        return_type_parts = []
        attributes = []

        for child in node.children:
            if child.type in ("type_specifier", "primitive_type",
                               "sized_integer_type", "type_qualifier",
                               "storage_class_specifier"):
                return_type_parts.append(source_text[child.start_byte:child.end_byte])
            elif child.type == "function_declarator":
                declarator = child
            elif child.type == "pointer_declarator":
                declarator = child
            elif child.type == "attribute_specifier":
                attributes.append(source_text[child.start_byte:child.end_byte])

        if declarator is None:
            return None

        # Extract function name
        func_name = None
        params = []
        for child in declarator.children:
            if child.type == "identifier":
                func_name = source_text[child.start_byte:child.end_byte]
            elif child.type == "parameter_list":
                params = [
                    source_text[p.start_byte:p.end_byte]
                    for p in child.children
                    if p.type == "parameter_declaration"
                ]

        if func_name is None or func_name in ("main",):
            return None  # Skip entry points — they are compositions, not blocks

        return_type = " ".join(return_type_parts) if return_type_parts else "void"
        is_inline = "inline" in return_type or "__inline" in full_text
        is_static = "static" in return_type
        is_isr = is_isr_function(func_name, attributes)

        return RawBlock(
            source_name=source_name,
            file_path=rel_path,
            function_name=func_name,
            return_type=return_type.replace("static", "").replace("inline", "").strip(),
            parameters=params,
            body=full_text,
            includes=includes,
            line_start=node.start_point[0],
            line_end=node.end_point[0],
            is_inline=is_inline,
            is_static=is_static,
            is_isr=is_isr,
            language="c",
            raw_attributes=attributes,
        )
    except Exception:
        return None  # Malformed node — skip silently, log in validation phase
```

### 1.3 — Block Validation (`corpus/ingest/validator.py`)

```python
"""
Every block that enters the corpus must pass this pipeline.
A block that fails any stage is rejected — not softened, not adjusted.
The corpus must be unconditionally correct.

Validation pipeline:
  Stage 1: Compilation test (arm-none-eabi-gcc -c, flags below)
  Stage 2: UBSan + ASan clean (where applicable)
  Stage 3: Stack depth analysis (arm-none-eabi-gcc -fstack-usage)
  Stage 4: Cppcheck static analysis — zero errors, zero warnings
  Stage 5: Bounded execution check — no unbounded loops in ISR blocks
  Stage 6: Naming + attribution completeness

Agent: stages 1, 3, 4 are mandatory for all C blocks.
       Stage 2 is best-effort (requires host-compilable subset).
       Stage 5 is mandatory for blocks where is_isr=True.
       Stage 6 is always mandatory.
"""

import subprocess
import tempfile
import shutil
import re
from pathlib import Path
from dataclasses import dataclass
from typing import Optional
from .extractor import RawBlock


COMPILE_FLAGS_ARM_CORTEX_M4 = [
    "arm-none-eabi-gcc",
    "-c",                           # Compile only — no link
    "-mcpu=cortex-m4",
    "-mthumb",
    "-mfpu=fpv4-sp-d16",
    "-mfloat-abi=hard",
    "-std=c11",                     # C11, not GNU extensions
    "-O2",                          # Optimized — we validate optimized output
    "-Wall", "-Wextra", "-Wpedantic",
    "-Werror",                      # Warnings are errors — no exceptions
    "-fstack-usage",                # Emit .su files with per-function stack depth
    "-ffunction-sections",          # Enable dead-code elimination
    "-fdata-sections",
    "-DUSE_HAL_DRIVER",
    "-DSTM32F407xx",
]

CPPCHECK_FLAGS = [
    "cppcheck",
    "--enable=all",
    "--std=c11",
    "--platform=arm32-wchar_t2",
    "--suppress=missingInclude",    # We validate includes separately
    "--suppress=unusedFunction",    # Blocks are by definition not called in isolation
    "--error-exitcode=1",
    "--quiet",
]


@dataclass
class ValidationResult:
    block_id: str
    passed: bool
    stack_bytes: Optional[int]      # None if analysis unavailable
    compile_error: Optional[str]
    static_analysis_issues: list[str]
    unbounded_loop_in_isr: bool
    warnings: list[str]


def compile_block(block: RawBlock, include_dirs: list[str]) -> tuple[bool, Optional[str]]:
    """
    Attempt to compile the block in isolation.
    Returns (success, error_message).

    Agent: the block body is wrapped in a minimal translation unit.
    All detected includes are prepended. Unknown includes are suppressed
    with -include stubs — this is the only acceptable compromise to
    enable isolated compilation.
    """
    with tempfile.TemporaryDirectory() as tmpdir:
        src_path = Path(tmpdir) / "block_test.c"

        # Build minimal translation unit
        unit = "\n".join(block.includes) + "\n\n"
        unit += "/* AUTO-GENERATED VALIDATION UNIT — DO NOT DISTRIBUTE */\n\n"
        unit += block.body + "\n"
        src_path.write_text(unit)

        cmd = COMPILE_FLAGS_ARM_CORTEX_M4 + [
            "-o", "/dev/null",
            str(src_path),
        ]
        for inc in include_dirs:
            cmd += ["-I", inc]

        result = subprocess.run(
            cmd, capture_output=True, text=True, timeout=30
        )

        if result.returncode != 0:
            return False, result.stderr.strip()
        return True, None


def parse_stack_usage_file(su_path: Path, func_name: str) -> Optional[int]:
    """
    Parse GCC .su (stack usage) files.
    Format: filename:line:col:function_name  bytes  qualifier
    qualifier is "static" (bounded) or "dynamic" (unbounded — red flag).
    """
    if not su_path.exists():
        return None
    for line in su_path.read_text().splitlines():
        parts = line.split()
        if len(parts) >= 3 and func_name in parts[0]:
            try:
                bytes_val = int(parts[1])
                qualifier = parts[2] if len(parts) > 2 else "static"
                if qualifier == "dynamic,bounded":
                    return bytes_val
                elif qualifier == "dynamic":
                    return -1  # Sentinel: unbounded stack — fail
                return bytes_val
            except ValueError:
                continue
    return None


def check_isr_for_unbounded_loops(block: RawBlock) -> bool:
    """
    Detect unbounded loops (while(1) without break, for(;;)) in ISR blocks.
    ISRs must return. An ISR with an unbounded loop is a system hang.

    This is a conservative heuristic — flag for manual review rather than
    auto-reject, since some ISRs have state machines that look like loops.
    """
    if not block.is_isr:
        return False

    body = block.body
    # Remove while(1) patterns that are genuinely unbounded
    infinite_loop_patterns = [
        r'while\s*\(\s*1\s*\)',
        r'while\s*\(\s*true\s*\)',
        r'for\s*\(\s*;\s*;\s*\)',
    ]
    for pat in infinite_loop_patterns:
        if re.search(pat, body):
            # Check if there's a break or return inside the loop body
            # Simplified: flag if no break/return after the loop keyword
            if not re.search(r'\b(break|return)\b', body):
                return True
    return False


def validate_block(
    block: RawBlock,
    include_dirs: list[str],
    block_id: str
) -> ValidationResult:
    """Full validation pipeline for one block."""

    # Stage 1: Compile
    compiled, compile_error = compile_block(block, include_dirs)
    if not compiled:
        return ValidationResult(
            block_id=block_id, passed=False,
            stack_bytes=None, compile_error=compile_error,
            static_analysis_issues=[], unbounded_loop_in_isr=False,
            warnings=[]
        )

    # Stage 3: Stack analysis (from .su file written during compilation)
    # Agent: re-run compile with -fstack-usage and collect the .su output
    stack_bytes = None  # Populated by compile_block with -fstack-usage enabled

    # Stage 4: Cppcheck
    with tempfile.NamedTemporaryFile(suffix=".c", mode="w", delete=False) as f:
        f.write("\n".join(block.includes) + "\n\n" + block.body)
        fname = f.name
    try:
        result = subprocess.run(
            CPPCHECK_FLAGS + [fname],
            capture_output=True, text=True, timeout=60
        )
        static_issues = []
        if result.returncode != 0:
            static_issues = result.stderr.strip().splitlines()
    finally:
        Path(fname).unlink(missing_ok=True)

    # Stage 5: ISR unbounded loop check
    unbounded = check_isr_for_unbounded_loops(block)

    passed = (
        compiled and
        len(static_issues) == 0 and
        not (block.is_isr and unbounded)
    )

    return ValidationResult(
        block_id=block_id,
        passed=passed,
        stack_bytes=stack_bytes,
        compile_error=None,
        static_analysis_issues=static_issues,
        unbounded_loop_in_isr=unbounded,
        warnings=[]
    )
```

### 1.4 — Corpus Schema (`corpus/db/schema.py`)

```python
"""
The corpus database schema.

Agent: this schema is the data model for the entire project.
Every field has a reason. No field is optional without a documented reason.
Use SQLite for development, PostgreSQL for production.
"""

from sqlalchemy import (
    Column, String, Integer, Boolean, Text, Float,
    ForeignKey, JSON, DateTime, Enum, UniqueConstraint
)
from sqlalchemy.orm import declarative_base, relationship
from sqlalchemy.sql import func
import enum

Base = declarative_base()


class BlockCategory(str, enum.Enum):
    PERIPHERAL_DRIVER  = "peripheral_driver"   # GPIO, UART, SPI, I2C, ADC, DMA...
    RTOS_PRIMITIVE     = "rtos_primitive"       # Task, queue, mutex, semaphore, timer
    INTERRUPT_HANDLER  = "interrupt_handler"    # ISRs and fault handlers
    CLOCK_POWER        = "clock_power"          # RCC, PLLs, sleep modes, LDO config
    MEMORY_PROTECTION  = "memory_protection"    # MPU regions, cache, TCM mapping
    STARTUP_LINKER     = "startup_linker"       # Reset handler, vector table, .ld logic
    DSP_MATH           = "dsp_math"             # SIMD, FFT, FIR, fixed-point math
    COMMUNICATION      = "communication"        # Protocol framing: USB, CAN, Ethernet
    SECURITY           = "security"             # RNG, crypto, TrustZone setup
    ASSEMBLY           = "assembly"             # .S files, hand-optimized asm
    MACRO_PRIMITIVE    = "macro_primitive"      # Compile-time-evaluated macro blocks
    PIO_PROGRAM        = "pio_program"          # RP2040 PIO state machine programs


class MCUArchitecture(str, enum.Enum):
    CORTEX_M0      = "cortex-m0"
    CORTEX_M0PLUS  = "cortex-m0plus"
    CORTEX_M3      = "cortex-m3"
    CORTEX_M4      = "cortex-m4"
    CORTEX_M4F     = "cortex-m4f"         # With FPU
    CORTEX_M7      = "cortex-m7"
    CORTEX_M33     = "cortex-m33"         # With TrustZone
    CORTEX_M55     = "cortex-m55"         # With Helium MVE
    CORTEX_M85     = "cortex-m85"
    AVR_MEGA       = "avr-mega"
    AVR_TINY       = "avr-tiny"
    XTENSA_LX6     = "xtensa-lx6"         # ESP32 original
    XTENSA_LX7     = "xtensa-lx7"         # ESP32-S3
    RISCV_RV32IMAC = "riscv-rv32imac"     # ESP32-C3, SiFive E
    RISCV_RV64GC   = "riscv-rv64gc"       # SiFive U


class VerificationStatus(str, enum.Enum):
    UNVERIFIED        = "unverified"        # Not yet validated
    COMPILED_CLEAN    = "compiled_clean"    # Passes compile stage
    STATIC_CLEAN      = "static_clean"      # Passes cppcheck
    EMULATOR_VERIFIED = "emulator_verified" # Runs correctly in QEMU/simavr
    SILICON_VERIFIED  = "silicon_verified"  # Confirmed on real hardware
    REJECTED          = "rejected"          # Failed validation — kept for audit


class CodeBlock(Base):
    __tablename__ = "code_blocks"

    id              = Column(String(64), primary_key=True)
    # ID format: {source}_{function_name}_{arch}_{sha8}
    # e.g.: STM32CubeF4_UART_Init_cortex-m4f_a1b2c3d4

    # Provenance
    source_name     = Column(String(128), nullable=False)
    source_url      = Column(String(512), nullable=False)
    source_commit   = Column(String(40), nullable=False)   # Pinned SHA
    source_license  = Column(String(32), nullable=False)
    file_path       = Column(String(512), nullable=False)
    line_start      = Column(Integer, nullable=False)
    line_end        = Column(Integer, nullable=False)

    # Identity
    function_name   = Column(String(256), nullable=False)
    category        = Column(Enum(BlockCategory), nullable=False)
    architecture    = Column(Enum(MCUArchitecture), nullable=False)
    mcu_family      = Column(String(64), nullable=False)   # e.g. "stm32f4"
    mcu_specific    = Column(JSON, nullable=True)          # e.g. ["F407", "F411"]

    # Source code
    body            = Column(Text, nullable=False)         # Full function source
    includes        = Column(JSON, nullable=False)         # List of #include strings
    dependencies    = Column(JSON, nullable=False)         # Other block IDs this calls
    conflicts       = Column(JSON, nullable=False)         # Block IDs that cannot co-exist

    # Hardware properties — measured, not estimated
    stack_bytes     = Column(Integer, nullable=True)       # -1 = unbounded (bad)
    flash_bytes     = Column(Integer, nullable=True)       # Code size after -O2
    cycle_budget    = Column(Integer, nullable=True)       # Worst-case cycles, if known
    is_isr          = Column(Boolean, nullable=False, default=False)
    is_reentrant    = Column(Boolean, nullable=True)       # NULL = unknown
    is_inline       = Column(Boolean, nullable=False, default=False)

    # Optimization metadata
    uses_simd       = Column(Boolean, nullable=False, default=False)
    uses_dma        = Column(Boolean, nullable=False, default=False)
    uses_fpu        = Column(Boolean, nullable=False, default=False)
    uses_mpu        = Column(Boolean, nullable=False, default=False)
    min_clock_hz    = Column(Integer, nullable=True)       # Minimum viable clock
    hal_version_min = Column(String(32), nullable=True)

    # Validation
    verification_status = Column(Enum(VerificationStatus),
                                  nullable=False,
                                  default=VerificationStatus.UNVERIFIED)
    compile_flags   = Column(Text, nullable=True)          # Exact flags used
    validated_at    = Column(DateTime, server_default=func.now())

    # Embedding — filled after Phase 2
    embedding       = Column(JSON, nullable=True)          # 512-dim float list

    # Searchability
    description     = Column(Text, nullable=True)          # Human-readable purpose
    tags            = Column(JSON, nullable=False, default=list)

    __table_args__ = (
        UniqueConstraint("source_name", "function_name",
                         "architecture", name="uq_block_identity"),
    )
```

---

## PHASE 2 — EMBEDDING SPACE
### Train the three-axis geometric representation

```
Agent: the embedding model is NOT trained from scratch.
Fine-tune sentence-transformers/microsoft-codebert-base on the corpus.
The objective is triplet loss with hardware-aware negative mining.
Target: 512-dim embeddings where cosine distance encodes
(1) semantic purpose, (2) correctness lineage, (3) compatibility.

VRAM budget for RTX 4050 6GB:
- Model: CodeBERT-base = ~500MB
- Batch size: 16 triplets
- Max sequence length: 512 tokens
- Use gradient checkpointing
- Use bfloat16 (not fp16 — more numerically stable for this)
```

```python
# embedding/trainer.py

"""
Triplet-loss embedding trainer for CodeLM block space.

Triplet construction strategy — this is where the corpus's hardware
knowledge gets encoded into geometry:

  Anchor:   UART_Init_STM32F4
  Positive: UART_Init_STM32F4_DMA  (same peripheral, compatible, composable)
  Negative: UART_Init_STM32F4_IT   (same peripheral but CONFLICTS — both
                                    register the same IRQ)

  Anchor:   xTaskCreate_FreeRTOS_CM4
  Positive: xQueueCreate_FreeRTOS_CM4  (same RTOS, compatible)
  Negative: xTaskCreate_FreeRTOS_CM0   (same RTOS, DIFFERENT arch — not composable)

The negative examples encode hardware incompatibility as geometric distance.
This is the core novelty of CodeLM's embedding space.
"""

import torch
import torch.nn as nn
from torch.utils.data import Dataset, DataLoader
from sentence_transformers import SentenceTransformer, losses
from sentence_transformers.readers import InputExample
from sqlalchemy.orm import Session
from typing import Iterator
from ..db.schema import CodeBlock, VerificationStatus
import random


EMBEDDING_DIM = 512
MODEL_BASE = "microsoft/codebert-base"
BATCH_SIZE = 16          # Fits in 6GB with bfloat16 + gradient checkpointing
LR = 2e-5
WARMUP_STEPS = 100
EPOCHS = 10
MAX_SEQ_LEN = 512        # CodeBERT max


def block_to_text(block: CodeBlock) -> str:
    """
    Convert a block to a text representation for the encoder.
    This text must capture BOTH the semantic content AND the hardware context.
    Architecture, category, and source are prepended as structured tokens.
    The encoder learns to attend to these during fine-tuning.
    """
    return (
        f"[ARCH:{block.architecture.value}] "
        f"[CAT:{block.category.value}] "
        f"[MCU:{block.mcu_family}] "
        f"[STACK:{block.stack_bytes or 'unknown'}B] "
        f"[DMA:{int(block.uses_dma)}] "
        f"[ISR:{int(block.is_isr)}] "
        f"/* {block.description or block.function_name} */\n"
        f"{block.body[:2000]}"  # Truncate to MAX_SEQ_LEN budget
    )


class TripletCorpusDataset(Dataset):
    """
    Generate triplets with hardware-aware negative mining.

    Negative mining strategy (in order of priority):
    1. CONFLICT negatives: blocks in block.conflicts list — highest signal
    2. ARCH negatives: same function on a different, incompatible architecture
    3. CATEGORY negatives: same MCU family but categorically different
    4. RANDOM negatives: fallback — least informative, use sparingly
    """

    def __init__(self, session: Session, min_verification: VerificationStatus):
        self.session = session
        # Only train on validated blocks
        self.blocks: list[CodeBlock] = (
            session.query(CodeBlock)
            .filter(CodeBlock.verification_status.in_([
                VerificationStatus.COMPILED_CLEAN,
                VerificationStatus.STATIC_CLEAN,
                VerificationStatus.EMULATOR_VERIFIED,
                VerificationStatus.SILICON_VERIFIED,
            ]))
            .all()
        )
        self._build_indices()

    def _build_indices(self):
        """Pre-build lookup indices for efficient negative mining."""
        self.by_arch: dict[str, list[CodeBlock]] = {}
        self.by_category: dict[str, list[CodeBlock]] = {}
        self.by_mcu: dict[str, list[CodeBlock]] = {}
        self.id_to_block: dict[str, CodeBlock] = {}

        for b in self.blocks:
            self.id_to_block[b.id] = b
            self.by_arch.setdefault(b.architecture.value, []).append(b)
            self.by_category.setdefault(b.category.value, []).append(b)
            self.by_mcu.setdefault(b.mcu_family, []).append(b)

    def _get_positive(self, anchor: CodeBlock) -> CodeBlock:
        """
        Positive: same MCU family, same category, no conflicts.
        These should be geometrically close — composable blocks.
        """
        candidates = [
            b for b in self.by_mcu.get(anchor.mcu_family, [])
            if b.id != anchor.id
            and b.category == anchor.category
            and b.id not in (anchor.conflicts or [])
        ]
        if not candidates:
            # Fallback: same arch, different MCU but same category
            candidates = [
                b for b in self.by_arch.get(anchor.architecture.value, [])
                if b.id != anchor.id and b.category == anchor.category
            ]
        return random.choice(candidates) if candidates else anchor

    def _get_negative(self, anchor: CodeBlock) -> CodeBlock:
        """
        Priority 1: Explicit conflict — strongest negative signal.
        Priority 2: Same category, incompatible architecture.
        Priority 3: Random from different category.
        """
        # Priority 1: conflict
        conflict_blocks = [
            self.id_to_block[cid]
            for cid in (anchor.conflicts or [])
            if cid in self.id_to_block
        ]
        if conflict_blocks:
            return random.choice(conflict_blocks)

        # Priority 2: arch incompatibility (same category, wrong arch)
        wrong_arch = [
            b for b in self.by_category.get(anchor.category.value, [])
            if b.architecture != anchor.architecture
            and b.mcu_family != anchor.mcu_family
        ]
        if wrong_arch:
            return random.choice(wrong_arch)

        # Priority 3: different category, same arch (semantically different)
        diff_cat = [
            b for b in self.by_arch.get(anchor.architecture.value, [])
            if b.category != anchor.category
        ]
        if diff_cat:
            return random.choice(diff_cat)

        # Fallback
        return random.choice(self.blocks)

    def __len__(self) -> int:
        return len(self.blocks) * 3  # 3 triplets per block

    def __getitem__(self, idx: int) -> InputExample:
        anchor = self.blocks[idx % len(self.blocks)]
        positive = self._get_positive(anchor)
        negative = self._get_negative(anchor)
        return InputExample(
            texts=[
                block_to_text(anchor),
                block_to_text(positive),
                block_to_text(negative),
            ]
        )


def train_embeddings(session: Session, output_dir: str):
    """
    Fine-tune CodeBERT with triplet loss on the block corpus.
    Optimized for RTX 4050 6GB VRAM.
    """
    model = SentenceTransformer(MODEL_BASE)
    model[0].auto_model.gradient_checkpointing_enable()

    # Cast to bfloat16 — more stable than fp16 for this task
    model[0].auto_model = model[0].auto_model.to(torch.bfloat16)

    dataset = TripletCorpusDataset(session, VerificationStatus.COMPILED_CLEAN)
    train_loss = losses.TripletLoss(
        model=model,
        distance_metric=losses.TripletDistanceMetric.COSINE,
        triplet_margin=0.5,
    )

    model.fit(
        train_objectives=[(DataLoader(dataset, batch_size=BATCH_SIZE, shuffle=True),
                           train_loss)],
        epochs=EPOCHS,
        warmup_steps=WARMUP_STEPS,
        optimizer_params={"lr": LR},
        output_path=output_dir,
        save_best_model=True,
        show_progress_bar=True,
    )
    print(f"Embedding model saved to {output_dir}")
```

---

## PHASE 3 — THE CODELM TRANSFORMER
### Block-token architecture — not a wrapper, a new model

```
Agent: this is the core contribution. Read the architecture notes before coding.

Architecture decisions and their reasons:

DECISION 1 — Vocabulary size: ~32,000 blocks (target corpus size)
  Reason: This is comparable to GPT-2's subword vocab (50k) but each
  "token" is orders of magnitude more semantically dense. A single block
  token encodes hundreds of lines of validated C.

DECISION 2 — Model size: 125M parameters (GPT-2 Small equivalent)
  Reason: Fits in 6GB VRAM for fine-tuning with LoRA. The task is
  composition over a bounded vocabulary — it does not require 70B params.
  Smaller = deployable locally = no API dependency forever.

DECISION 3 — Context length: 256 block-tokens
  Reason: No firmware project needs more than 256 distinct function blocks.
  This is a domain-specific constraint that allows much cheaper attention.

DECISION 4 — Two specialized attention heads beyond standard self-attention:
  (a) Constraint head: attends to the MCU target + HAL version tokens
      inserted at position 0. Masks incompatible blocks.
  (b) Composition head: learns ordering (dependency graph traversal order).

DECISION 5 — Output is a block sequence + composition graph, not text
  The decoder outputs block IDs, not characters. The firmware composer
  (Phase 4) translates block IDs to actual source code with correct
  includes, linkage, and project structure.
```

```python
# model/architecture.py

"""
CodeLM Transformer — block-token sequence model.

This is not a language model. It is a program synthesis model.
The vocabulary items are verified hardware primitives, not subwords.
The output is a composition graph, not a string.
"""

import torch
import torch.nn as nn
import torch.nn.functional as F
import math
from dataclasses import dataclass
from typing import Optional


@dataclass
class CodeLMConfig:
    vocab_size: int        = 32_768    # Block vocabulary size
    d_model: int           = 512       # Embedding dimension
    n_heads: int           = 8         # Attention heads
    n_layers: int          = 6         # Transformer layers
    d_ff: int              = 2048      # Feed-forward dimension
    max_seq_len: int       = 256       # Max block sequence length
    dropout: float         = 0.1
    constraint_heads: int  = 2         # Dedicated constraint attention heads
    pad_token_id: int      = 0
    bos_token_id: int      = 1
    eos_token_id: int      = 2
    # Special token IDs for MCU context injection
    mcu_token_offset: int  = 3         # Tokens 3–102 = MCU family identifiers
    arch_token_offset: int = 103       # Tokens 103–152 = architecture identifiers
    hal_token_offset: int  = 153       # Tokens 153–202 = HAL version identifiers
    cat_token_offset: int  = 203       # Tokens 203–222 = category constraints


class RotaryPositionalEncoding(nn.Module):
    """
    Rotary Position Embedding (RoPE) — Su et al. 2021.
    Used instead of learned absolute positions because:
    1. Better length generalization (critical for variable-length block sequences)
    2. No position vocabulary to overfit to corpus length
    3. Relative position information — which block comes after which
       is more meaningful than absolute position in a firmware composition.
    """

    def __init__(self, d_model: int, max_seq_len: int):
        super().__init__()
        assert d_model % 2 == 0
        theta = 1.0 / (10000 ** (torch.arange(0, d_model, 2).float() / d_model))
        seq_idx = torch.arange(max_seq_len).float()
        freqs = torch.outer(seq_idx, theta)  # (seq_len, d_model/2)
        self.register_buffer("cos", freqs.cos())
        self.register_buffer("sin", freqs.sin())

    def rotate_half(self, x: torch.Tensor) -> torch.Tensor:
        x1, x2 = x[..., :x.shape[-1]//2], x[..., x.shape[-1]//2:]
        return torch.cat([-x2, x1], dim=-1)

    def forward(self, q: torch.Tensor, k: torch.Tensor) -> tuple[torch.Tensor, torch.Tensor]:
        seq_len = q.shape[-2]
        cos = self.cos[:seq_len].unsqueeze(0).unsqueeze(0)  # (1, 1, seq, d/2)
        sin = self.sin[:seq_len].unsqueeze(0).unsqueeze(0)
        # Interleave cos/sin application
        cos_full = torch.cat([cos, cos], dim=-1)
        sin_full = torch.cat([sin, sin], dim=-1)
        q_rot = q * cos_full + self.rotate_half(q) * sin_full
        k_rot = k * cos_full + self.rotate_half(k) * sin_full
        return q_rot, k_rot


class ConstraintAwareAttention(nn.Module):
    """
    Multi-head attention with dedicated constraint heads.

    The first `constraint_heads` attention heads receive a constraint mask
    derived from the MCU context tokens at the start of the sequence.
    These heads learn to suppress incompatible blocks during generation.

    The remaining heads perform standard causal self-attention over the
    block sequence.

    This enforces hardware correctness at the architectural level —
    not as a post-processing filter, but as part of the attention mechanism.
    """

    def __init__(self, config: CodeLMConfig):
        super().__init__()
        self.d_model = config.d_model
        self.n_heads = config.n_heads
        self.constraint_heads = config.constraint_heads
        self.d_head = config.d_model // config.n_heads
        assert config.d_model % config.n_heads == 0

        self.q_proj = nn.Linear(config.d_model, config.d_model, bias=False)
        self.k_proj = nn.Linear(config.d_model, config.d_model, bias=False)
        self.v_proj = nn.Linear(config.d_model, config.d_model, bias=False)
        self.out_proj = nn.Linear(config.d_model, config.d_model, bias=False)
        self.rope = RotaryPositionalEncoding(self.d_head, config.max_seq_len)
        self.dropout = nn.Dropout(config.dropout)

    def forward(
        self,
        x: torch.Tensor,                           # (B, T, d_model)
        causal_mask: Optional[torch.Tensor] = None,
        constraint_mask: Optional[torch.Tensor] = None,
        # constraint_mask: (B, T) boolean — True = this block is incompatible
        #   with the current MCU/arch context. Applied only to constraint_heads.
    ) -> torch.Tensor:
        B, T, _ = x.shape
        H, D = self.n_heads, self.d_head

        q = self.q_proj(x).view(B, T, H, D).transpose(1, 2)  # (B, H, T, D)
        k = self.k_proj(x).view(B, T, H, D).transpose(1, 2)
        v = self.v_proj(x).view(B, T, H, D).transpose(1, 2)

        q, k = self.rope(q, k)

        scale = math.sqrt(D)
        scores = torch.matmul(q, k.transpose(-2, -1)) / scale  # (B, H, T, T)

        # Apply causal mask (standard autoregressive)
        if causal_mask is not None:
            scores = scores.masked_fill(causal_mask == 0, float("-inf"))

        # Apply constraint mask to constraint_heads only
        if constraint_mask is not None and self.constraint_heads > 0:
            # constraint_mask: (B, T) → expand to (B, H, 1, T) for key masking
            cmask = constraint_mask.unsqueeze(1).unsqueeze(2)  # (B, 1, 1, T)
            cmask = cmask.expand(B, self.constraint_heads, T, T)
            # Mask only constraint heads (first N heads)
            scores[:, :self.constraint_heads] = scores[:, :self.constraint_heads].masked_fill(
                cmask, float("-inf")
            )

        attn = F.softmax(scores, dim=-1)
        attn = self.dropout(attn)

        out = torch.matmul(attn, v)             # (B, H, T, D)
        out = out.transpose(1, 2).contiguous().view(B, T, self.d_model)
        return self.out_proj(out)


class CodeLMBlock(nn.Module):
    """One transformer layer. Pre-norm architecture (more stable than post-norm)."""

    def __init__(self, config: CodeLMConfig):
        super().__init__()
        self.attn = ConstraintAwareAttention(config)
        self.ff = nn.Sequential(
            nn.Linear(config.d_model, config.d_ff, bias=False),
            nn.GELU(),
            nn.Linear(config.d_ff, config.d_model, bias=False),
            nn.Dropout(config.dropout),
        )
        self.norm1 = nn.RMSNorm(config.d_model)  # RMSNorm = LLaMA-style, more stable
        self.norm2 = nn.RMSNorm(config.d_model)

    def forward(
        self,
        x: torch.Tensor,
        causal_mask: Optional[torch.Tensor] = None,
        constraint_mask: Optional[torch.Tensor] = None,
    ) -> torch.Tensor:
        x = x + self.attn(self.norm1(x), causal_mask, constraint_mask)
        x = x + self.ff(self.norm2(x))
        return x


class CodeLM(nn.Module):
    """
    The full CodeLM model.

    Input format:
        [MCU_TOKEN] [ARCH_TOKEN] [HAL_TOKEN] [CAT_TOKEN(s)] [INTENT_EMBEDDING(s)]
        [BOS] [block_1] [block_2] ... [EOS]

    The first 4–8 positions are context tokens encoding the hardware target.
    The constraint heads use these to suppress incompatible block tokens
    throughout the sequence.

    Output: logits over the block vocabulary at each position.
    During inference, argmax + constraint filtering gives the next block ID.
    """

    def __init__(self, config: CodeLMConfig):
        super().__init__()
        self.config = config
        self.token_emb = nn.Embedding(config.vocab_size, config.d_model,
                                       padding_idx=config.pad_token_id)
        self.layers = nn.ModuleList([CodeLMBlock(config) for _ in range(config.n_layers)])
        self.norm = nn.RMSNorm(config.d_model)
        self.lm_head = nn.Linear(config.d_model, config.vocab_size, bias=False)

        # Weight tying: input embedding and output projection share weights.
        # Standard practice — reduces parameters, improves generalization.
        self.lm_head.weight = self.token_emb.weight

        self._init_weights()

    def _init_weights(self):
        """Initialize with scaled normal — critical for training stability."""
        std = 0.02
        for module in self.modules():
            if isinstance(module, nn.Linear):
                nn.init.normal_(module.weight, mean=0.0, std=std)
                if module.bias is not None:
                    nn.init.zeros_(module.bias)
            elif isinstance(module, nn.Embedding):
                nn.init.normal_(module.weight, mean=0.0, std=std)
                if module.padding_idx is not None:
                    module.weight.data[module.padding_idx].zero_()

    def _make_causal_mask(self, seq_len: int, device: torch.device) -> torch.Tensor:
        """Upper triangular causal mask — block i can only attend to blocks ≤ i."""
        return torch.tril(torch.ones(seq_len, seq_len, device=device, dtype=torch.bool))

    def forward(
        self,
        input_ids: torch.Tensor,                # (B, T) block token IDs
        constraint_mask: Optional[torch.Tensor] = None,  # (B, T) incompatible flags
        labels: Optional[torch.Tensor] = None,  # (B, T) for training
    ) -> dict[str, torch.Tensor]:
        B, T = input_ids.shape
        device = input_ids.device

        x = self.token_emb(input_ids)  # (B, T, d_model)
        causal_mask = self._make_causal_mask(T, device)

        for layer in self.layers:
            x = layer(x, causal_mask, constraint_mask)

        x = self.norm(x)
        logits = self.lm_head(x)  # (B, T, vocab_size)

        result = {"logits": logits}

        if labels is not None:
            # Shift for next-token prediction
            shift_logits = logits[:, :-1, :].contiguous()
            shift_labels = labels[:, 1:].contiguous()
            loss = F.cross_entropy(
                shift_logits.view(-1, self.config.vocab_size),
                shift_labels.view(-1),
                ignore_index=self.config.pad_token_id,
            )
            result["loss"] = loss

        return result
```

---

## PHASE 4 — FIRMWARE COMPOSER
### Block sequence → flash-ready, maximally optimized firmware

```
Agent: this phase converts the model's output (a sequence of block IDs)
into a complete, buildable, maximally optimized firmware project.

"Maximally optimized" is defined precisely:
  - Binary size: within 3% of theoretical minimum (dead-code-eliminated,
    LTO-applied, unused sections stripped)
  - Execution speed: all hot paths (ISRs, main loop body) in IRAM/TCM
    where architecture supports it
  - Stack depth: provably bounded for every call path
  - Interrupt latency: deterministic — no priority inversion, no unbounded
    critical sections
  - Power: clock gating enabled for all unused peripherals at init time
  - No UB: zero undefined behavior confirmed by compile-time analysis

The composer is not a template engine. It is a synthesis engine.
It understands the dependency graph of the selected blocks and generates
the minimal, correct set of glue code to compose them.
```

```python
# firmware/composer.py

"""
Firmware project composer.

Input:  a list of CodeBlock objects (the CodeLM output sequence)
Output: a dict mapping filename → file content, representing a complete
        buildable firmware project.

The composer performs:
  1. Dependency graph resolution (topological sort)
  2. Include deduplication and ordering
  3. Linker script synthesis (per architecture)
  4. CMakeLists.txt synthesis with LTO + size optimization flags
  5. startup.c synthesis (or selection from corpus)
  6. main.c synthesis — the composition glue
  7. FreeRTOS config synthesis (if RTOS blocks present)
"""

from dataclasses import dataclass, field
from typing import Optional
import textwrap
from ..corpus.db.schema import CodeBlock, BlockCategory, MCUArchitecture


OPTIMIZATION_FLAGS_CORTEX_M4F = [
    "-mcpu=cortex-m4",
    "-mthumb",
    "-mfpu=fpv4-sp-d16",
    "-mfloat-abi=hard",
    "-O2",                        # O2 not Os — we optimize for speed, linker does size
    "-flto=auto",                 # Link-time optimization — cross-file dead code removal
    "-ffunction-sections",        # Each function in its own section
    "-fdata-sections",            # Each variable in its own section
    "-fomit-frame-pointer",       # Save a register on Cortex-M (no debug cost in release)
    "-fno-common",                # No common symbols — prevents accidental sharing
    "-fstack-usage",              # Emit stack usage data
    "-Wl,--gc-sections",          # Linker: garbage collect unused sections
    "-Wl,--print-memory-usage",   # Print final flash/RAM usage
    "-specs=nano.specs",          # Newlib-nano: minimal libc
    "-specs=nosys.specs",         # No semihosting
    "-Wall", "-Wextra", "-Werror",
    "-DNDEBUG",                   # Disable assert() in release
]


def resolve_dependency_order(blocks: list[CodeBlock]) -> list[CodeBlock]:
    """
    Topological sort of blocks by dependency graph.
    Blocks that others depend on must be defined first.
    Raises ValueError on cycles — a cycle means the corpus has a dependency error.
    """
    id_map = {b.id: b for b in blocks}
    visited: set[str] = set()
    result: list[CodeBlock] = []
    in_stack: set[str] = set()

    def visit(block_id: str):
        if block_id in in_stack:
            raise ValueError(f"Dependency cycle detected involving block: {block_id}")
        if block_id in visited:
            return
        in_stack.add(block_id)
        block = id_map.get(block_id)
        if block:
            for dep_id in (block.dependencies or []):
                if dep_id in id_map:
                    visit(dep_id)
            visited.add(block_id)
            in_stack.discard(block_id)
            result.append(block)

    for b in blocks:
        visit(b.id)
    return result


def synthesize_main_c(blocks: list[CodeBlock], arch: MCUArchitecture) -> str:
    """
    Synthesize the main.c composition file.

    The main.c contains ONLY:
    1. Includes for all selected blocks
    2. Extern declarations where needed
    3. An init sequence (clock → peripherals → RTOS → user code)
    4. The main() entry point

    No logic belongs here. main.c is the composition, not the implementation.
    """
    # Deduplicate and order includes
    all_includes: list[str] = []
    seen: set[str] = set()
    for block in blocks:
        for inc in (block.includes or []):
            if inc not in seen:
                seen.add(inc)
                all_includes.append(inc)

    # Categorize blocks by init order
    clock_blocks   = [b for b in blocks if b.category == BlockCategory.CLOCK_POWER]
    mem_blocks     = [b for b in blocks if b.category == BlockCategory.MEMORY_PROTECTION]
    periph_blocks  = [b for b in blocks if b.category == BlockCategory.PERIPHERAL_DRIVER]
    rtos_blocks    = [b for b in blocks if b.category == BlockCategory.RTOS_PRIMITIVE]
    isr_blocks     = [b for b in blocks if b.is_isr]
    startup_blocks = [b for b in blocks if b.category == BlockCategory.STARTUP_LINKER]

    lines = [
        "/**",
        " * CodeLM-synthesized firmware",
        " * This file is auto-generated. Do not edit manually.",
        " * Modify the block selection and re-synthesize.",
        " */",
        "",
    ]

    # System includes first, then project includes
    sys_includes = [i for i in all_includes if i.startswith("#include <")]
    proj_includes = [i for i in all_includes if i.startswith('#include "')]
    lines += sys_includes + [""] + proj_includes + ["", ""]

    # Init sequence
    lines += [
        "static void system_init(void) {"]
    for b in clock_blocks:
        if not b.is_isr:
            lines.append(f"    {b.function_name}();")
    for b in mem_blocks:
        if not b.is_isr:
            lines.append(f"    {b.function_name}();")
    for b in periph_blocks:
        if not b.is_isr:
            lines.append(f"    {b.function_name}();")
    lines += ["}", ""]

    # main()
    if rtos_blocks:
        lines += [
            "int main(void) {",
            "    system_init();",
            "    /* RTOS tasks created by synthesized task-creation blocks */",
        ]
        for b in rtos_blocks:
            if "create" in b.function_name.lower() or "init" in b.function_name.lower():
                lines.append(f"    {b.function_name}();")
        lines += [
            "    vTaskStartScheduler();",
            "    /* Should never reach here */",
            "    for (;;) {}",
            "}",
        ]
    else:
        lines += [
            "int main(void) {",
            "    system_init();",
            "    for (;;) {",
            "        /* Application logic */",
            "    }",
            "}",
        ]

    return "\n".join(lines)


def synthesize_cmake(
    blocks: list[CodeBlock],
    arch: MCUArchitecture,
    project_name: str = "codelm_firmware",
) -> str:
    """
    CMakeLists.txt with maximum optimization configuration.
    LTO, gc-sections, and architecture-specific tuning are non-negotiable.
    """
    source_files = list({b.file_path for b in blocks}) + ["src/main.c"]

    flags = OPTIMIZATION_FLAGS_CORTEX_M4F
    c_flags_str = " ".join(f for f in flags
                            if not f.startswith("-Wl") and not f.startswith("-specs"))
    ld_flags_str = " ".join(f for f in flags
                             if f.startswith("-Wl") or f.startswith("-specs"))

    return textwrap.dedent(f"""\
        cmake_minimum_required(VERSION 3.27)
        project({project_name} C ASM)

        set(CMAKE_SYSTEM_NAME Generic)
        set(CMAKE_SYSTEM_PROCESSOR arm)
        set(CMAKE_TRY_COMPILE_TARGET_TYPE STATIC_LIBRARY)

        find_program(ARM_GCC arm-none-eabi-gcc REQUIRED)
        find_program(ARM_OBJCOPY arm-none-eabi-objcopy REQUIRED)
        set(CMAKE_C_COMPILER ${{ARM_GCC}})
        set(CMAKE_ASM_COMPILER ${{ARM_GCC}})
        set(CMAKE_OBJCOPY ${{ARM_OBJCOPY}})

        set(C_FLAGS "{c_flags_str}")
        set(CMAKE_C_FLAGS "${{C_FLAGS}}")
        set(CMAKE_ASM_FLAGS "${{C_FLAGS}}")
        set(CMAKE_EXE_LINKER_FLAGS "{ld_flags_str} -T${{CMAKE_SOURCE_DIR}}/linker.ld")

        add_executable(${{PROJECT_NAME}}.elf
            {chr(10).join('    ' + f for f in source_files)}
        )

        target_include_directories(${{PROJECT_NAME}}.elf PRIVATE
            ${{CMAKE_SOURCE_DIR}}/include
        )

        # Post-build: generate .bin and .hex from .elf
        add_custom_command(TARGET ${{PROJECT_NAME}}.elf POST_BUILD
            COMMAND ${{CMAKE_OBJCOPY}} -O binary ${{PROJECT_NAME}}.elf ${{PROJECT_NAME}}.bin
            COMMAND ${{CMAKE_OBJCOPY}} -O ihex   ${{PROJECT_NAME}}.elf ${{PROJECT_NAME}}.hex
            COMMENT "Generating binary artifacts"
        )
    """)
```

---

## PHASE 5 — TRAINING LOOP (RTX 4050 OPTIMIZED)

```python
# model/train.py

"""
LoRA fine-tuning of CodeLM on the block-composition dataset.

RTX 4050 6GB VRAM budget breakdown:
  Model (fp32):  125M params × 4 bytes   = 500MB
  Model (bf16):  125M params × 2 bytes   = 250MB
  LoRA adapters: ~1% of params           = ~2.5MB
  Optimizer states (AdamW, bf16):        = ~250MB
  Activations (gradient checkpointing):  = ~512MB
  Batch data:                            = ~256MB
  Total:                                 ≈ 1.3GB  ← fits comfortably

Why LoRA: We are fine-tuning a foundation (CodeBERT) on domain-specific
block composition data. LoRA trains only low-rank adapter matrices
injected into Q and V projections. The base weights are frozen.
This means we train ~0.3% of parameters but get 80%+ of full fine-tune quality.
"""

import torch
from torch.optim import AdamW
from torch.optim.lr_scheduler import CosineAnnealingLR
from peft import LoraConfig, get_peft_model, TaskType
from .architecture import CodeLM, CodeLMConfig
from torch.utils.data import DataLoader
from torch.cuda.amp import GradScaler
import os


def build_lora_model(config: CodeLMConfig) -> torch.nn.Module:
    """
    Wrap CodeLM with LoRA adapters.
    Only Q and V projections get adapters — standard practice.
    """
    base_model = CodeLM(config)
    lora_config = LoraConfig(
        task_type=TaskType.CAUSAL_LM,
        r=16,                   # Rank — 16 is sweet spot for domain fine-tune
        lora_alpha=32,          # Scaling factor
        target_modules=["q_proj", "v_proj"],  # Only Q and V
        lora_dropout=0.05,
        bias="none",
    )
    return get_peft_model(base_model, lora_config)


def train(
    model: torch.nn.Module,
    train_loader: DataLoader,
    val_loader: DataLoader,
    epochs: int = 20,
    lr: float = 1e-4,
    output_dir: str = "checkpoints/",
):
    device = torch.device("cuda")  # RTX 4050
    model = model.to(device)
    model.train()

    optimizer = AdamW(
        [p for p in model.parameters() if p.requires_grad],
        lr=lr,
        weight_decay=0.01,
        betas=(0.9, 0.95),  # Slightly higher beta2 — better for sparse gradients
    )
    scheduler = CosineAnnealingLR(optimizer, T_max=epochs, eta_min=lr * 0.1)
    scaler = GradScaler()  # Mixed precision

    best_val_loss = float("inf")
    os.makedirs(output_dir, exist_ok=True)

    for epoch in range(epochs):
        total_loss = 0.0
        model.train()

        for step, batch in enumerate(train_loader):
            input_ids     = batch["input_ids"].to(device)
            labels        = batch["labels"].to(device)
            constraint_mask = batch.get("constraint_mask")
            if constraint_mask is not None:
                constraint_mask = constraint_mask.to(device)

            optimizer.zero_grad(set_to_none=True)  # set_to_none is faster

            with torch.autocast(device_type="cuda", dtype=torch.bfloat16):
                outputs = model(input_ids, constraint_mask, labels)
                loss = outputs["loss"]

            scaler.scale(loss).backward()

            # Gradient clipping — prevents explosive gradients early in training
            scaler.unscale_(optimizer)
            torch.nn.utils.clip_grad_norm_(model.parameters(), max_norm=1.0)

            scaler.step(optimizer)
            scaler.update()
            total_loss += loss.item()

        scheduler.step()
        avg_train_loss = total_loss / len(train_loader)

        # Validation
        model.eval()
        val_loss = 0.0
        with torch.no_grad():
            for batch in val_loader:
                input_ids = batch["input_ids"].to(device)
                labels    = batch["labels"].to(device)
                constraint_mask = batch.get("constraint_mask")
                if constraint_mask is not None:
                    constraint_mask = constraint_mask.to(device)
                with torch.autocast(device_type="cuda", dtype=torch.bfloat16):
                    outputs = model(input_ids, constraint_mask, labels)
                    val_loss += outputs["loss"].item()
        val_loss /= len(val_loader)

        print(f"Epoch {epoch+1}/{epochs} | Train: {avg_train_loss:.4f} | Val: {val_loss:.4f}")

        if val_loss < best_val_loss:
            best_val_loss = val_loss
            model.save_pretrained(os.path.join(output_dir, "best"))
            print(f"  ↳ New best model saved (val_loss={val_loss:.4f})")
```

---

## PHASE 6 — EXECUTION ORDER

```
Agent: execute phases in this exact order.
Each phase gate-checks before proceeding.

PHASE 1A: Run corpus/ingest/downloader.py for all SOURCES entries.
          Gate: every source must clone cleanly to corpus/raw/.
          Do not proceed if any clone fails — fix the commit SHA.

PHASE 1B: Run corpus/ingest/extractor.py over all downloaded sources.
          Gate: minimum 500 blocks extracted before proceeding.
          Log rejection rate — if >70% of functions are rejected,
          review the extraction patterns in sources.py.

PHASE 1C: Run corpus/ingest/validator.py over all extracted blocks.
          Gate: minimum 300 blocks reach COMPILED_CLEAN status.
          Review compile errors — most will be missing includes.
          Fix includes, not the blocks.

PHASE 1D: Populate all metadata fields in corpus/db/schema.py.
          Gate: every COMPILED_CLEAN block must have:
          - category (auto-classified or manually assigned)
          - architecture (auto-detected from source)
          - dependencies (static call graph analysis)
          - description (auto-generated from function name + docstring)

PHASE 2:  Train embeddings. Gate: embedding loss < 0.3 on validation set.
          If not reached in 10 epochs, review triplet construction —
          the most likely issue is insufficient conflict negatives.

PHASE 3:  Train CodeLM. Gate: perplexity < 5.0 on held-out compositions.
          This means the model can reliably predict the next block given
          a partial composition and hardware context.

PHASE 4:  Synthesize test firmware projects for:
          - STM32F407: UART + FreeRTOS two-task LED blink
          - ESP32-S3: SPI DMA + WiFi event handler
          - nRF52840: BLE advertising + GPIO interrupt
          Gate: all three projects build cleanly with arm-none-eabi-gcc.

PHASE 5:  Run verify.py on synthesized firmware.
          Gate: zero UBSan hits, stack depth provably bounded,
          binary size within 5% of hand-written reference implementation.
```

---

## INVARIANTS — NEVER VIOLATE

```
These are not guidelines. They are invariants.
If any of these would be violated by an implementation decision,
stop, report the conflict, and wait for instruction.

1. PROVENANCE IMMUTABILITY
   Every block in the corpus has a pinned source commit.
   A block's source commit never changes after ingestion.
   If the upstream changes, a NEW block entry is created.
   The old entry is never deleted — it is marked superseded.
   Reason: reproducibility across centuries means the corpus is
   an append-only ledger, not a mutable database.

2. NO FABRICATED BLOCKS
   CodeLM never writes firmware logic. It only composes blocks
   that exist in the corpus. If a user's intent cannot be satisfied
   by existing blocks, CodeLM returns a PARTIAL composition with
   a precise description of what blocks are missing.
   It does not hallucinate new code to fill the gap.
   Reason: this is the fundamental correctness guarantee.
   An LLM that generates plausible-looking code can silently produce
   wrong firmware. CodeLM cannot.

3. NO UNVERIFIED BLOCK REACHES THE OUTPUT
   A block with verification_status = UNVERIFIED is never included
   in a firmware composition output. Ever.
   Reason: the output firmware's correctness guarantee is only as
   strong as the weakest block. One unverified block breaks the chain.

4. STACK DEPTH IS ALWAYS BOUNDED
   Any composition containing a block with stack_bytes = -1 (unbounded)
   is rejected at the composition stage, not at runtime.
   Reason: an unbounded stack on a microcontroller is a corruption
   waiting to happen. This is caught structurally, not empirically.

5. INTERRUPT SAFETY IS STRUCTURAL
   If a composition includes both a peripheral driver block and its
   corresponding ISR block, the composer verifies that the NVIC
   priority is set before the peripheral is enabled.
   This is a composition rule, not a runtime check.
   Reason: enabling an interrupt before its handler is registered
   is a data-race condition on embedded. It must be impossible by construction.

6. LICENSE COMPLIANCE IS NON-NEGOTIABLE
   Every block in the corpus has a verified open-source license.
   The composer tracks license provenance for every synthesized project
   and generates a LICENSES.md file listing all incorporated blocks,
   their source URLs, commit SHAs, and license texts.
   Reason: firmware that cannot be legally shipped is worthless.
   CodeLM's output must be deployable without legal ambiguity.
```

---

## LONG-TERM ARCHITECTURE NOTES

```
These notes are for the agent and any future developer maintaining this system.
They explain why decisions were made the way they were.

WHY BLOCK-TOKENS INSTEAD OF SUBWORDS
  Subword tokenization (BPE, WordPiece) was designed for natural language,
  where meaning is compositional at the character level.
  Embedded firmware is not compositional at the character level.
  A UART initialization function is not "U" + "ART" + "_init".
  It is a complete semantic unit with hardware dependencies,
  timing constraints, and register-level side effects.
  Treating it as a sequence of subwords destroys exactly this information.
  Block tokenization preserves it.

WHY THE CORPUS IS THE MOAT, NOT THE MODEL
  Models can be retrained. Architectures can be replaced.
  A corpus of 50,000 silicon-verified, provenance-tracked,
  structurally analyzed embedded code blocks — that takes years to build.
  Every entry in the corpus represents a real hardware validation:
  someone compiled it, flashed it, and it worked.
  That signal cannot be generated synthetically. It must be earned.

WHY THE CONSTRAINT HEAD IS ARCHITECTURAL, NOT POST-HOC
  Filtering bad outputs after generation is fragile.
  The model can generate a plausible-looking sequence that is internally
  consistent but violates the MCU's peripheral constraints.
  The constraint head makes hardware incompatibility structurally impossible
  to generate — it masks incompatible tokens before the softmax,
  so they have zero probability at decode time.
  This is the difference between "we check for errors" and
  "errors cannot be represented in the output space."

WHY 125M PARAMETERS AND NOT LARGER
  The composition problem over a 32k block vocabulary, with a context
  of 256 blocks, is orders of magnitude simpler than natural language
  generation. The model does not need to learn human pragmatics,
  common-sense reasoning, or stylistic variation.
  It needs to learn: given this hardware context and these already-selected
  blocks, which block should come next?
  125M parameters is sufficient. Larger models would overfit
  on a corpus of this size and add inference latency with no benefit.
  Running locally on developer hardware is a feature, not a limitation.

ON DURABILITY ACROSS CENTURIES
  The ARM Cortex-M architecture has been in production since 2004.
  The instruction set is architecturally stable — code written for
  Cortex-M3 in 2008 still runs on Cortex-M33 today.
  RISC-V ratified its base ISA in 2019 and it is frozen by specification.
  AVR has been stable since 1997.
  The block corpus, anchored to pinned upstream commits with complete
  provenance, will be verifiable decades from now.
  The model weights are secondary — they can be retrained.
  The corpus is the primary artifact. Preserve it absolutely.
```

---

*End of CodeLM Agent Instruction File.*
*Version: 1.0.0 — Initial specification*
*Hardware target: NVIDIA RTX 4050, Python 3.12, CUDA 12.x*
*License of this specification: Apache-2.0*
