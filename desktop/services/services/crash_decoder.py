"""
Crash Decoder — Decode ESP32 Guru Meditation, STM32 HardFault, RP2040 panic dumps.

Parses crash dumps and provides:
  - Decoded exception type and cause
  - Register state interpretation
  - Stack trace with function suggestions
  - Common fix suggestions based on crash pattern
"""

import re
from dataclasses import dataclass, field
from typing import Optional


@dataclass
class CrashReport:
    platform: str  # esp32, stm32, rp2040
    exception_type: str = ""
    cause: str = ""
    pc: str = ""  # Program Counter
    registers: dict = field(default_factory=dict)
    backtrace: list[str] = field(default_factory=list)
    suggestions: list[str] = field(default_factory=list)
    severity: str = "critical"


class CrashDecoder:
    """Decode crash dumps from embedded platforms."""

    # ESP32 exception causes
    ESP32_EXCEPTIONS = {
        "0": "IllegalInstructionCause — Invalid opcode",
        "2": "InstructionFetchError — Code at invalid address",
        "3": "LoadStoreError — Read/write invalid address",
        "6": "IntegerDivideByZero",
        "9": "LoadStoreAlignmentCause — Unaligned memory access",
        "12": "InstrPIFDataError — PIF bus error on instruction fetch",
        "13": "LoadStorePIFDataError — PIF bus error on data access",
        "14": "InstrPIFAddrError — PIF address error on instruction",
        "15": "LoadStorePIFAddrError — PIF address error on data",
        "20": "InstTLBMissCause — ITLB miss",
        "24": "LoadStoreTLBMissCause — DTLB miss",
        "28": "Coprocessor0Disabled",
        "29": "ExcCause:29 — Possible stack overflow",
    }

    # STM32 fault types
    STM32_FAULTS = {
        "HardFault": "Generic hard fault — CPU cannot determine cause",
        "MemManage": "Memory management fault — MPU violation",
        "BusFault": "Bus error — invalid memory access",
        "UsageFault": "Usage fault — undefined instruction, unaligned, div by zero",
    }

    def decode(self, dump: str) -> dict:
        """Decode a crash dump and return structured report."""
        dump_lower = dump.lower()

        if "guru meditation" in dump_lower or "esp32" in dump_lower:
            report = self._decode_esp32(dump)
        elif "hardfault" in dump_lower or "stm32" in dump_lower or "busfault" in dump_lower:
            report = self._decode_stm32(dump)
        elif "panic" in dump_lower and ("rp2040" in dump_lower or "pico" in dump_lower):
            report = self._decode_rp2040(dump)
        else:
            report = CrashReport(platform="unknown", exception_type="Unrecognized crash format")
            report.suggestions = ["Paste the full crash output from serial monitor"]

        return {
            "platform": report.platform,
            "exception": report.exception_type,
            "cause": report.cause,
            "pc": report.pc,
            "registers": report.registers,
            "backtrace": report.backtrace,
            "suggestions": report.suggestions,
            "severity": report.severity,
        }

    def _decode_esp32(self, dump: str) -> CrashReport:
        report = CrashReport(platform="esp32")

        # Extract exception cause
        excvaddr = re.search(r'EXCVADDR\s*:\s*(0x[0-9a-fA-F]+)', dump)
        exccause = re.search(r'EXCCAUSE\s*:\s*(\d+)', dump)

        if exccause:
            cause_id = exccause.group(1)
            report.exception_type = self.ESP32_EXCEPTIONS.get(cause_id, f"Unknown ExcCause:{cause_id}")
            report.cause = f"Exception cause {cause_id}"

        if excvaddr:
            report.registers["EXCVADDR"] = excvaddr.group(1)
            addr = int(excvaddr.group(1), 16)
            if addr == 0:
                report.suggestions.append("🔴 NULL pointer dereference — check all pointer variables before use")
            elif addr < 0x1000:
                report.suggestions.append("🔴 Accessing very low address — likely uninitialized pointer or struct field access on NULL")
            elif addr > 0x40000000:
                report.suggestions.append("⚠️ Accessing peripheral register space — verify register address in chip datasheet")

        # Extract PC
        pc_match = re.search(r'PC\s*:\s*(0x[0-9a-fA-F]+)', dump)
        if pc_match:
            report.pc = pc_match.group(1)

        # Extract backtrace
        bt_match = re.search(r'Backtrace:\s*(.*?)(?:\n|$)', dump)
        if bt_match:
            addrs = re.findall(r'(0x[0-9a-fA-F]+)', bt_match.group(1))
            report.backtrace = addrs[:10]

        # Extract registers
        for reg in ["EPC1", "EPC2", "EPC3", "EPCNMI", "SAR", "PS", "A0", "A1", "A2", "A3"]:
            match = re.search(rf'{reg}\s*:\s*(0x[0-9a-fA-F]+)', dump)
            if match:
                report.registers[reg] = match.group(1)

        # Guru Meditation parsing
        guru = re.search(r'Guru Meditation Error: Core\s*(\d+)\s*panic.*?\((.*?)\)', dump)
        if guru:
            report.cause = f"Core {guru.group(1)} panic: {guru.group(2)}"
            panic_type = guru.group(2).lower()
            if "stackoverflow" in panic_type or "stack" in panic_type:
                report.suggestions.append("📦 Stack overflow — increase task stack size or reduce local variables")
                report.suggestions.append("💡 FreeRTOS: use uxTaskGetStackHighWaterMark() to check remaining stack")
            elif "loadprohibited" in panic_type:
                report.suggestions.append("🔴 LoadProhibited — accessing memory that is not readable (NULL ptr or out of bounds)")
            elif "storeprohibited" in panic_type:
                report.suggestions.append("🔴 StoreProhibited — writing to read-only or unmapped memory")

        # Generic suggestions
        if not report.suggestions:
            report.suggestions = [
                "📋 Use addr2line to decode backtrace addresses to source lines",
                "💡 Check for stack overflow by increasing task stack sizes",
                "🔍 Verify all pointers are initialized before use",
            ]

        return report

    def _decode_stm32(self, dump: str) -> CrashReport:
        report = CrashReport(platform="stm32")

        for fault, desc in self.STM32_FAULTS.items():
            if fault.lower() in dump.lower():
                report.exception_type = fault
                report.cause = desc
                break

        # Extract registers
        for reg in ["R0", "R1", "R2", "R3", "R12", "LR", "PC", "PSR", "CFSR", "HFSR", "MMFAR", "BFAR"]:
            match = re.search(rf'{reg}\s*[=:]\s*(0x[0-9a-fA-F]+)', dump, re.IGNORECASE)
            if match:
                report.registers[reg] = match.group(1)

        pc_match = report.registers.get("PC")
        if pc_match:
            report.pc = pc_match

        # CFSR analysis
        cfsr = report.registers.get("CFSR")
        if cfsr:
            cfsr_val = int(cfsr, 16)
            if cfsr_val & 0x0100:
                report.suggestions.append("🔴 IBUSERR — Instruction bus error, check code alignment")
            if cfsr_val & 0x0200:
                report.suggestions.append("🔴 PRECISERR — Precise data bus error, check pointer")
            if cfsr_val & 0x0400:
                report.suggestions.append("⚠️ IMPRECISERR — Imprecise data bus error")
            if cfsr_val & 0x0001:
                report.suggestions.append("🔴 IACCVIOL — Instruction access violation, MPU fault")
            if cfsr_val & 0x0002:
                report.suggestions.append("🔴 DACCVIOL — Data access violation, writing to read-only memory")

        if not report.suggestions:
            report.suggestions = [
                "📋 Decode PC address using arm-none-eabi-addr2line -e firmware.elf",
                "🔍 Check for stack overflow — compare SP with stack bounds",
                "⚡ Verify all interrupt handlers are properly defined",
            ]

        return report

    def _decode_rp2040(self, dump: str) -> CrashReport:
        report = CrashReport(platform="rp2040")
        report.exception_type = "RP2040 Panic"

        panic_match = re.search(r'panic\("(.+?)"\)', dump)
        if panic_match:
            report.cause = panic_match.group(1)

        pc_match = re.search(r'pc\s*=\s*(0x[0-9a-fA-F]+)', dump, re.IGNORECASE)
        if pc_match:
            report.pc = pc_match.group(1)

        report.suggestions = [
            "📋 Use picotool to decode crash address",
            "🔍 Check for alignment issues — RP2040 requires aligned access for XIP flash",
            "💡 Verify PIO programs are valid (PIO crashes are hard to debug)",
        ]

        return report


def get_crash_decoder() -> CrashDecoder:
    return CrashDecoder()
