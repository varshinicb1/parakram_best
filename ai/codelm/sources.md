
## Everything to download into the CodeLM workspace

Run these in order inside `codelm/corpus/raw/`. These are the **only** authoritative sources — vendor-controlled, pinned to current stable releases, all permissive licenses.

---

### TIER 1 — The absolute floor (clone these first)

**1. CMSIS-6** — ARM's current Cortex-M hardware abstraction (CMSIS-5 was archived Dec 2025)
```bash
git clone https://github.com/ARM-software/CMSIS_6.git
cd CMSIS_6 && git checkout main   # Use latest tagged release
```
→ https://github.com/ARM-software/CMSIS_6

**2. CMSIS-DSP** — SIMD-optimized signal processing, now its own repo
```bash
git clone https://github.com/ARM-software/CMSIS-DSP.git
```
→ https://github.com/ARM-software/CMSIS-DSP

**3. CMSIS-NN** — Neural net inference kernels for Cortex-M, now its own repo
```bash
git clone https://github.com/ARM-software/CMSIS-NN.git
```
→ https://github.com/ARM-software/CMSIS-NN

**4. FreeRTOS-Kernel** — The kernel only, no demos, cleanest repo
```bash
git clone https://github.com/FreeRTOS/FreeRTOS-Kernel.git
cd FreeRTOS-Kernel && git checkout V11.1.0
```
→ https://github.com/FreeRTOS/FreeRTOS-Kernel/releases/tag/V11.1.0

---

### TIER 2 — Vendor SDKs (the actual peripheral drivers)

**5. STM32CubeF4** — F407/F411/F446, the most widely used Cortex-M4F family
```bash
git clone https://github.com/STMicroelectronics/STM32CubeF4.git --depth=1
```
→ https://github.com/STMicroelectronics/STM32CubeF4
Size warning: ~2GB with examples. Use `--depth=1` to get just latest.

**6. STM32CubeH7** — H743/H750, Cortex-M7 with L1 cache + TCM
```bash
git clone https://github.com/STMicroelectronics/STM32CubeH7.git --depth=1
```
→ https://github.com/STMicroelectronics/STM32CubeH7

**7. STM32CubeWL** — WL55, sub-GHz LoRa radio (unique radio driver blocks)
```bash
git clone https://github.com/STMicroelectronics/STM32CubeWL.git --depth=1
```
→ https://github.com/STMicroelectronics/STM32CubeWL

**8. stm32-ll-drivers standalone** — LL (Low-Layer) drivers extracted separately, zero HAL overhead
```bash
git clone https://github.com/STMicroelectronics/stm32f4xx-ll-driver.git
```
→ https://github.com/STMicroelectronics/stm32f4xx-ll-driver

**9. esp-idf** — ESP32/S3/C3/C6, the only correct ESP32 source (not Arduino)
```bash
git clone --recursive https://github.com/espressif/esp-idf.git
cd esp-idf && git checkout v5.2.1
```
→ https://github.com/espressif/esp-idf/releases/tag/v5.2.1
Note: `--recursive` needed for submodules. Large repo (~1.5GB).

**10. pico-sdk** — RP2040 + RP2350, PIO state machine programs are unique
```bash
git clone https://github.com/raspberrypi/pico-sdk.git
cd pico-sdk && git checkout 2.2.0 && git submodule update --init
```
→ https://github.com/raspberrypi/pico-sdk/releases/tag/2.2.0

**11. nrfx** — Nordic's HAL, standalone, Zephyr-compatible, cleanest driver code in embedded
```bash
git clone https://github.com/NordicSemiconductor/nrfx.git
cd nrfx && git checkout v3.5.0
```
→ https://github.com/NordicSemiconductor/nrfx/releases

---

### TIER 3 — RTOS and OS kernel layer

**12. Zephyr** — The most rigorous driver model in open-source embedded
```bash
git clone https://github.com/zephyrproject-rtos/zephyr.git --depth=1
```
→ https://github.com/zephyrproject-rtos/zephyr
Only need `drivers/`, `kernel/`, `arch/` — not the full tree. Sparse checkout saves ~3GB:
```bash
git clone --filter=blob:none --sparse https://github.com/zephyrproject-rtos/zephyr.git
cd zephyr
git sparse-checkout set drivers kernel arch include
```

**13. avr-libc** — 8-bit Harvard, the most constraint-disciplined C ever written
```bash
git clone https://github.com/avrdudes/avr-libc.git
```
→ https://github.com/avrdudes/avr-libc

**14. freedom-metal** — SiFive's bare-metal RISC-V BSP, CLINT/PLIC reference implementation
```bash
git clone https://github.com/sifive/freedom-metal.git
```
→ https://github.com/sifive/freedom-metal

---

### TIER 4 — Communication stacks (protocol-layer blocks)

**15. TinyUSB** — USB device/host stack, runs on 15+ MCU families
```bash
git clone https://github.com/hathach/tinyusb.git
cd tinyusb && git checkout 0.17.0
```
→ https://github.com/hathach/tinyusb/releases

**16. lwIP** — Lightweight TCP/IP, the reference for embedded networking
```bash
git clone https://git.savannah.nongnu.org/git/lwip.git
# Mirror on GitHub:
git clone https://github.com/lwip-tcpip/lwip.git
```
→ https://github.com/lwip-tcpip/lwip

**17. MbedTLS** — Crypto + TLS for embedded, used by FreeRTOS, ESP-IDF, Zephyr
```bash
git clone https://github.com/Mbed-TLS/mbedtls.git
cd mbedtls && git checkout v3.6.0
```
→ https://github.com/Mbed-TLS/mbedtls/releases/tag/v3.6.0

**18. LoRaMac-node** — The reference LoRaWAN stack, used by ST/Semtech officially
```bash
git clone https://github.com/Lora-net/LoRaMac-node.git
```
→ https://github.com/Lora-net/LoRaMac-node

---

### TIER 5 — Static analysis + tooling (not corpus, but required by validator)

Install these as system tools, not into `corpus/raw/`:

```bash
# ARM cross-compiler (the only compiler that matters for validation)
sudo apt-get install gcc-arm-none-eabi binutils-arm-none-eabi

# RISC-V cross-compiler
sudo apt-get install gcc-riscv64-unknown-elf

# AVR cross-compiler
sudo apt-get install avr-libc gcc-avr

# Static analysis
sudo apt-get install cppcheck clang clang-tools

# QEMU for emulator-level validation
sudo apt-get install qemu-system-arm qemu-system-misc

# For ESP32 (Xtensa toolchain — must use espressif's own)
pip install esptool
# Full Xtensa GCC is installed by esp-idf's install script:
cd corpus/raw/esp-idf && ./install.sh esp32,esp32s3,esp32c3
```

---

### Disk space estimate

| Source | Approx size |
|---|---|
| CMSIS-6 + DSP + NN | ~300MB |
| STM32CubeF4 + H7 + WL (depth=1) | ~1.5GB |
| esp-idf (recursive) | ~1.5GB |
| pico-sdk + submodules | ~400MB |
| nrfx | ~80MB |
| Zephyr (sparse) | ~400MB |
| FreeRTOS-Kernel | ~20MB |
| avr-libc + freedom-metal | ~50MB |
| TinyUSB + lwIP + MbedTLS | ~200MB |
| **Total** | **~4.5GB** |

Make sure you have **at least 10GB free** — the extractor generates intermediate files during block processing.

---

### One-shot clone script

Save this as `codelm/corpus/raw/clone_all.sh` and run it once:

```bash
#!/bin/bash
set -e  # Stop on first failure

echo "=== CodeLM Corpus Source Cloner ==="
echo "Requires ~5GB free disk space"

# TIER 1
git clone https://github.com/ARM-software/CMSIS_6.git
git clone https://github.com/ARM-software/CMSIS-DSP.git
git clone https://github.com/ARM-software/CMSIS-NN.git
git clone https://github.com/FreeRTOS/FreeRTOS-Kernel.git
(cd FreeRTOS-Kernel && git checkout V11.1.0)

# TIER 2
git clone https://github.com/STMicroelectronics/STM32CubeF4.git --depth=1
git clone https://github.com/STMicroelectronics/STM32CubeH7.git --depth=1
git clone https://github.com/STMicroelectronics/stm32f4xx-ll-driver.git
git clone --recursive https://github.com/espressif/esp-idf.git
(cd esp-idf && git checkout v5.2.1 && ./install.sh esp32,esp32s3,esp32c3)
git clone https://github.com/raspberrypi/pico-sdk.git
(cd pico-sdk && git checkout 2.2.0 && git submodule update --init)
git clone https://github.com/NordicSemiconductor/nrfx.git

# TIER 3
git clone --filter=blob:none --sparse https://github.com/zephyrproject-rtos/zephyr.git
(cd zephyr && git sparse-checkout set drivers kernel arch include)
git clone https://github.com/avrdudes/avr-libc.git
git clone https://github.com/sifive/freedom-metal.git

# TIER 4
git clone https://github.com/hathach/tinyusb.git
(cd tinyusb && git checkout 0.17.0)
git clone https://github.com/lwip-tcpip/lwip.git
git clone https://github.com/Mbed-TLS/mbedtls.git
(cd mbedtls && git checkout v3.6.0)
git clone https://github.com/Lora-net/LoRaMac-node.git

echo ""
echo "=== All sources cloned. ==="
echo "Run corpus/ingest/extractor.py next."
```

That's everything. Once this finishes cloning, the agent has the complete raw material for the corpus — every line of code from an authoritative, vendor-controlled source, all permissive licenses, all pinnable to exact commits.
