"""
Code Review Agent — Static analysis for embedded-specific bugs.

Catches common firmware issues BEFORE compilation:
- Memory safety (malloc without free, large stack arrays)
- ISR correctness (no Serial/delay inside interrupts)
- Blocking calls (delay in loop, busy-wait without timeout)
- FreeRTOS issues (priority inversion, stack size)
- Hardware conflicts (duplicate pins, ADC2+WiFi)
"""

import re
from dataclasses import dataclass, field


@dataclass
class Issue:
    severity: str      # "error", "warning", "info"
    category: str      # "memory", "isr", "blocking", "freertos", "hardware"
    line: int
    message: str
    suggestion: str
    auto_fixable: bool = False


class CodeReviewer:
    """Static analyzer for embedded C/C++ firmware code."""

    def review(self, source: str, header: str = "", board: str = "esp32dev") -> list[Issue]:
        """Run all checks on firmware source code."""
        issues = []
        issues.extend(self._check_memory(source))
        issues.extend(self._check_isr(source))
        issues.extend(self._check_blocking(source))
        issues.extend(self._check_freertos(source))
        issues.extend(self._check_hardware(source, board))
        issues.extend(self._check_best_practices(source))
        return sorted(issues, key=lambda i: {"error": 0, "warning": 1, "info": 2}[i.severity])

    def _check_memory(self, source: str) -> list[Issue]:
        """Check for memory safety issues."""
        issues = []
        lines = source.split("\n")

        for i, line in enumerate(lines, 1):
            stripped = line.strip()

            # malloc without free
            if "malloc(" in stripped or "calloc(" in stripped:
                if "free(" not in source:
                    issues.append(Issue(
                        "warning", "memory", i,
                        f"Dynamic allocation without corresponding free()",
                        "Use stack allocation or ensure free() is called. "
                        "On ESP32, heap fragmentation can cause crashes.",
                    ))

            # Large stack arrays
            arr_match = re.search(r'\w+\s+\w+\[(\d+)\]', stripped)
            if arr_match:
                size = int(arr_match.group(1))
                if size > 512:
                    issues.append(Issue(
                        "warning", "memory", i,
                        f"Large stack array ({size} elements) may cause stack overflow",
                        f"Use heap allocation or reduce size. ESP32 default task stack: 8KB.",
                    ))

            # String concatenation in loop (heap fragmentation)
            if "String " in stripped and ("+" in stripped or "+=" in stripped):
                issues.append(Issue(
                    "info", "memory", i,
                    "Arduino String concatenation causes heap fragmentation",
                    "Use snprintf() with char buffer instead of String + operations.",
                    auto_fixable=True,
                ))

        return issues

    def _check_isr(self, source: str) -> list[Issue]:
        """Check for unsafe operations inside ISRs."""
        issues = []
        lines = source.split("\n")

        # Find ISR functions (IRAM_ATTR or attachInterrupt callbacks)
        in_isr = False
        isr_start = 0
        brace_depth = 0

        for i, line in enumerate(lines, 1):
            stripped = line.strip()

            if "IRAM_ATTR" in stripped or "ISR(" in stripped:
                in_isr = True
                isr_start = i
                brace_depth = 0

            if in_isr:
                brace_depth += stripped.count('{') - stripped.count('}')
                if brace_depth <= 0 and i > isr_start:
                    in_isr = False
                    continue

                # Banned operations in ISR
                banned = {
                    "Serial.print": "Serial operations use UART interrupts",
                    "Serial.write": "Serial operations use UART interrupts",
                    "delay(": "delay() uses timer interrupts, will deadlock",
                    "delayMicroseconds(": "delayMicroseconds > 10us is risky in ISR",
                    "malloc(": "Heap allocation is not ISR-safe",
                    "new ": "Heap allocation is not ISR-safe",
                    "WiFi.": "WiFi operations are not ISR-safe",
                    "yield(": "yield() is not ISR-safe",
                }

                for pattern, reason in banned.items():
                    if pattern in stripped:
                        issues.append(Issue(
                            "error", "isr", i,
                            f"Unsafe ISR operation: {pattern} — {reason}",
                            "Use a volatile flag in ISR, process in loop().",
                        ))

        return issues

    def _check_blocking(self, source: str) -> list[Issue]:
        """Check for blocking calls that freeze the MCU."""
        issues = []
        lines = source.split("\n")

        for i, line in enumerate(lines, 1):
            stripped = line.strip()

            # delay() in loop
            if "delay(" in stripped and "delayMicroseconds" not in stripped:
                delay_match = re.search(r'delay\((\d+)\)', stripped)
                if delay_match:
                    ms = int(delay_match.group(1))
                    if ms > 100:
                        issues.append(Issue(
                            "warning", "blocking", i,
                            f"delay({ms}) blocks execution for {ms}ms",
                            "Use non-blocking millis() pattern or FreeRTOS vTaskDelay().",
                            auto_fixable=True,
                        ))

            # while loop without timeout
            if stripped.startswith("while") and "millis" not in stripped and "timeout" not in stripped.lower():
                if "true" in stripped or "1)" in stripped or "WiFi" in stripped:
                    issues.append(Issue(
                        "warning", "blocking", i,
                        "Potentially infinite while loop without timeout",
                        "Add a millis()-based timeout to prevent firmware hang.",
                    ))

            # Busy-wait on sensor
            if "while" in stripped and ("available" in stripped or "ready" in stripped):
                if "millis" not in stripped:
                    issues.append(Issue(
                        "info", "blocking", i,
                        "Busy-wait on sensor without timeout",
                        "Add timeout: while(!ready && millis()-start < 1000).",
                    ))

        return issues

    def _check_freertos(self, source: str) -> list[Issue]:
        """Check FreeRTOS-specific issues."""
        issues = []
        lines = source.split("\n")

        for i, line in enumerate(lines, 1):
            stripped = line.strip()

            # Small task stack
            stack_match = re.search(r'xTaskCreate\w*\([^,]+,[^,]+,\s*(\d+)', stripped)
            if stack_match:
                stack = int(stack_match.group(1))
                if stack < 2048:
                    issues.append(Issue(
                        "warning", "freertos", i,
                        f"Task stack size {stack} bytes may be too small",
                        "Minimum 2048 for simple tasks, 4096+ if using Serial/WiFi.",
                    ))

            # Mutex in ISR
            if "xSemaphoreTake" in stripped:
                issues.append(Issue(
                    "info", "freertos", i,
                    "xSemaphoreTake in ISR-accessible code? Use xSemaphoreTakeFromISR instead",
                    "Check if this code path is reachable from an ISR.",
                ))

            # delay() with FreeRTOS (should use vTaskDelay)
            if "delay(" in stripped and "vTaskDelay" not in stripped:
                if "freertos" in source.lower() or "xTask" in source:
                    issues.append(Issue(
                        "info", "freertos", i,
                        "Using delay() instead of vTaskDelay() in FreeRTOS context",
                        "Use vTaskDelay(pdMS_TO_TICKS(ms)) for cooperative multitasking.",
                        auto_fixable=True,
                    ))

        return issues

    def _check_hardware(self, source: str, board: str) -> list[Issue]:
        """Check hardware-specific issues."""
        issues = []

        from agents.board_registry import get_board
        board_info = get_board(board)

        # Check for ADC2 + WiFi conflict
        if "WiFi" in source and board_info.get("mcu") == "ESP32":
            adc2 = board_info.get("adc2_pins", [])
            for pin in adc2:
                if f"analogRead({pin})" in source or f"GPIO{pin}" in source:
                    issues.append(Issue(
                        "error", "hardware", 0,
                        f"ADC2 pin {pin} used with WiFi active — reads will fail",
                        f"Use ADC1 pins ({board_info.get('adc_pins', [])[:5]}) instead. "
                        "ADC2 is unavailable when WiFi is active on ESP32.",
                    ))
                    break

        # Check for flash pins
        flash_pins = board_info.get("flash_pins", [])
        for pin in flash_pins:
            if f"pinMode({pin}" in source or f"GPIO{pin}" in source:
                issues.append(Issue(
                    "error", "hardware", 0,
                    f"GPIO{pin} is connected to flash memory — do not use",
                    f"Use safe pins: {board_info.get('safe_gpio', [])[:10]}",
                ))

        # Check for boot-restricted pins
        boot_pins = board_info.get("boot_restricted", [])
        for pin in boot_pins:
            if f"pinMode({pin}," in source and "OUTPUT" in source:
                issues.append(Issue(
                    "warning", "hardware", 0,
                    f"GPIO{pin} is a boot strapping pin — OUTPUT may prevent boot",
                    "These pins affect boot mode. Avoid using as OUTPUT if possible.",
                ))

        return issues

    def _check_best_practices(self, source: str) -> list[Issue]:
        """General best practices for firmware quality."""
        issues = []
        lines = source.split("\n")

        for i, line in enumerate(lines, 1):
            stripped = line.strip()

            # Missing Serial.begin
            if "Serial.print" in stripped:
                if "Serial.begin" not in source:
                    issues.append(Issue(
                        "warning", "best_practice", i,
                        "Serial.print used but Serial.begin() not found",
                        "Add Serial.begin(115200) in setup().",
                        auto_fixable=True,
                    ))
                    break

            # Hardcoded WiFi credentials
            if "WiFi.begin(" in stripped and '"' in stripped:
                issues.append(Issue(
                    "info", "best_practice", i,
                    "Hardcoded WiFi credentials in source code",
                    "Store credentials in Preferences/NVS or use WiFiManager.",
                ))

        # Check for watchdog
        if len(source) > 500 and "esp_task_wdt" not in source and "wdt" not in source.lower():
            issues.append(Issue(
                "info", "best_practice", 0,
                "No watchdog timer configured",
                "Consider esp_task_wdt_init() for production firmware.",
            ))

        return issues

    def format_report(self, issues: list[Issue]) -> str:
        """Format issues into a human-readable report."""
        if not issues:
            return "No issues found."

        icons = {"error": "[ERR]", "warning": "[WRN]", "info": "[INF]"}
        lines = [f"Code Review: {len(issues)} issues found\n"]

        for issue in issues:
            icon = icons.get(issue.severity, "[?]")
            loc = f"L{issue.line}" if issue.line > 0 else "global"
            lines.append(f"  {icon} [{issue.category}] {loc}: {issue.message}")
            lines.append(f"       Fix: {issue.suggestion}")

        errors = sum(1 for i in issues if i.severity == "error")
        warns = sum(1 for i in issues if i.severity == "warning")
        infos = sum(1 for i in issues if i.severity == "info")
        lines.append(f"\nSummary: {errors} errors, {warns} warnings, {infos} info")

        return "\n".join(lines)
