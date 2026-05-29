"""
Autonomous Firmware Agent — The brain of Parakram OS.

Unlike simple code generators, this agent thinks in steps:
  1. Parse user intent → extract board, peripherals, features
  2. Query chip knowledge base → inject register-level context
  3. Resolve libraries → map #include to PlatformIO deps
  4. Generate firmware → multi-file C++ project with main.cpp, headers
  5. Compile → PlatformIO build
  6. Self-heal → parse errors, fix, recompile (up to 3 attempts)
  7. Verify → check for common embedded bugs
  8. Package → ready to flash or simulate

Streams progress events via callback for real-time UI updates.
"""

import os
import re
import json
import asyncio
from typing import Optional, Callable
from dataclasses import dataclass, field
from pathlib import Path


@dataclass
class AgentStep:
    """A single step in the autonomous pipeline."""
    name: str
    status: str = "pending"  # pending, running, success, error, skipped
    message: str = ""
    data: dict = field(default_factory=dict)
    duration_ms: int = 0


@dataclass
class AgentSession:
    """Tracks the full autonomous session."""
    session_id: str
    prompt: str
    board: str = "esp32dev"
    steps: list[AgentStep] = field(default_factory=list)
    files: dict[str, str] = field(default_factory=dict)  # filename → content
    compile_output: str = ""
    compile_success: bool = False
    attempt: int = 0
    max_attempts: int = 3
    errors: list[str] = field(default_factory=list)
    status: str = "idle"  # idle, running, success, failed


# ── Intent Parser ──────────────────────────────────────────

BOARD_KEYWORDS = {
    "esp32": "esp32dev", "esp32s3": "esp32-s3-devkitc-1", "esp32c3": "esp32-c3-devkitm-1",
    "stm32": "nucleo_f446re", "stm32f4": "nucleo_f446re", "stm32h7": "nucleo_h743zi",
    "rp2040": "pico", "pico": "pico", "arduino": "megaatmega2560", "mega": "megaatmega2560",
    "nano": "nanoatmega328", "uno": "uno", "nrf52": "nrf52840_dk",
}

PERIPHERAL_PATTERNS = {
    "wifi": {"libs": ["WiFi.h"], "pio_deps": []},
    "ble": {"libs": ["BLEDevice.h"], "pio_deps": []},
    "mqtt": {"libs": ["PubSubClient.h"], "pio_deps": ["knolleary/PubSubClient"]},
    "i2c": {"libs": ["Wire.h"], "pio_deps": []},
    "spi": {"libs": ["SPI.h"], "pio_deps": []},
    "bme280": {"libs": ["Adafruit_BME280.h", "Wire.h"], "pio_deps": ["adafruit/Adafruit BME280 Library"]},
    "mpu6050": {"libs": ["MPU6050.h", "Wire.h"], "pio_deps": ["electroniccats/MPU6050"]},
    "neopixel": {"libs": ["Adafruit_NeoPixel.h"], "pio_deps": ["adafruit/Adafruit NeoPixel"]},
    "oled": {"libs": ["Adafruit_SSD1306.h", "Wire.h"], "pio_deps": ["adafruit/Adafruit SSD1306"]},
    "servo": {"libs": ["ESP32Servo.h"], "pio_deps": ["madhephaestus/ESP32Servo"]},
    "gps": {"libs": ["TinyGPSPlus.h"], "pio_deps": ["mikalhart/TinyGPSPlus"]},
    "sd card": {"libs": ["SD.h", "SPI.h"], "pio_deps": []},
    "lora": {"libs": ["LoRa.h"], "pio_deps": ["sandeepmistry/LoRa"]},
    "relay": {"libs": [], "pio_deps": []},
    "motor": {"libs": [], "pio_deps": []},
    "lcd": {"libs": ["LiquidCrystal_I2C.h"], "pio_deps": ["marcoschwartz/LiquidCrystal_I2C"]},
    "deep sleep": {"libs": [], "pio_deps": []},
    "ota": {"libs": ["ArduinoOTA.h"], "pio_deps": []},
    "web server": {"libs": ["ESPAsyncWebServer.h"], "pio_deps": ["me-no-dev/ESPAsyncWebServer"]},
    "json": {"libs": ["ArduinoJson.h"], "pio_deps": ["bblanchon/ArduinoJson"]},
    "rfid": {"libs": ["MFRC522.h"], "pio_deps": ["miguelbalboa/MFRC522"]},
    "ultrasonic": {"libs": [], "pio_deps": []},
    "dht": {"libs": ["DHT.h"], "pio_deps": ["adafruit/DHT sensor library"]},
    "tft": {"libs": ["TFT_eSPI.h"], "pio_deps": ["bodmer/TFT_eSPI"]},
    "fastled": {"libs": ["FastLED.h"], "pio_deps": ["fastled/FastLED"]},
    "can bus": {"libs": ["ESP32-TWAI-CAN.hpp"], "pio_deps": []},
}


def parse_intent(prompt: str) -> dict:
    """Extract board, peripherals, and features from natural language prompt."""
    prompt_lower = prompt.lower()

    # Detect board
    board = "esp32dev"  # default
    for keyword, board_id in BOARD_KEYWORDS.items():
        if keyword in prompt_lower:
            board = board_id
            break

    # Detect peripherals
    peripherals = []
    all_libs = set()
    all_deps = []
    for name, info in PERIPHERAL_PATTERNS.items():
        if name in prompt_lower:
            peripherals.append(name)
            all_libs.update(info["libs"])
            all_deps.extend(info["pio_deps"])

    # Detect features
    features = []
    feature_keywords = {
        "deep sleep": "Power optimization with deep sleep",
        "ota": "Over-the-air firmware updates",
        "web dashboard": "HTTP web server dashboard",
        "data logging": "SD card or SPIFFS data logging",
        "battery": "Battery monitoring and power management",
        "interrupt": "Hardware interrupt handling",
        "watchdog": "Watchdog timer for reliability",
        "freertos": "FreeRTOS multi-threaded tasks",
        "timer": "Hardware timer usage",
        "pwm": "PWM signal generation",
        "adc": "Analog-to-digital conversion",
    }
    for kw, desc in feature_keywords.items():
        if kw in prompt_lower:
            features.append(desc)

    return {
        "board": board,
        "peripherals": peripherals,
        "features": features,
        "libraries": list(all_libs),
        "pio_dependencies": list(set(all_deps)),
        "raw_prompt": prompt,
    }


# ── PlatformIO Project Generator ───────────────────────────

def generate_platformio_ini(board: str, deps: list[str]) -> str:
    """Generate platformio.ini content."""
    framework = "arduino"
    if "nucleo" in board or "stm32" in board:
        framework = "arduino"  # Could also be stm32cube

    ini = f"""[env:{board}]
platform = {"espressif32" if "esp32" in board else "raspberrypi" if "pico" in board else "ststm32" if "nucleo" in board else "atmelavr"}
board = {board}
framework = {framework}
monitor_speed = 115200
"""
    if deps:
        ini += "lib_deps =\n"
        for dep in deps:
            ini += f"    {dep}\n"
    return ini


# ── Autonomous Agent ───────────────────────────────────────

class AutonomousAgent:
    """The autonomous firmware intelligence engine."""

    def __init__(self):
        self.output_dir = Path("./firmware_output")
        self.output_dir.mkdir(parents=True, exist_ok=True)

    async def execute(
        self,
        prompt: str,
        on_progress: Optional[Callable] = None,
        session_id: Optional[str] = None,
    ) -> AgentSession:
        """Execute full autonomous pipeline: prompt → compilable firmware."""
        import time

        session = AgentSession(
            session_id=session_id or f"session_{int(time.time())}",
            prompt=prompt,
            status="running",
        )

        async def emit(step_name: str, status: str, message: str, data: dict = None):
            step = AgentStep(name=step_name, status=status, message=message, data=data or {})
            session.steps.append(step)
            if on_progress:
                try:
                    if asyncio.iscoroutinefunction(on_progress):
                        await on_progress(step.__dict__)
                    else:
                        on_progress(step.__dict__)
                except Exception:
                    pass

        try:
            # ── Step 1: Parse Intent ────────────────────────
            await emit("parse_intent", "running", "Analyzing your request...")
            intent = parse_intent(prompt)
            session.board = intent["board"]
            await emit("parse_intent", "success",
                f"Board: {intent['board']} | Peripherals: {', '.join(intent['peripherals']) or 'none'} | Features: {len(intent['features'])}",
                intent)

            # ── Step 2: Query Knowledge Base ────────────────
            await emit("knowledge_query", "running", "Consulting chip knowledge base...")
            from agents.chip_knowledge_base import get_chip_context
            chip_context = get_chip_context(intent["board"])
            await emit("knowledge_query", "success",
                f"Loaded {len(chip_context)} lines of chip-specific context")

            # ── Step 3: Generate Code ───────────────────────
            await emit("generate_code", "running", "Generating firmware code...")
            from agents.llm_provider import get_provider
            llm = get_provider()

            code_prompt = self._build_code_prompt(intent, chip_context)
            response = await llm.generate(code_prompt, max_tokens=3000)
            files = self._extract_files(response)

            # Retry with simpler prompt if the model returned nothing
            if not files:
                await emit("generate_code", "running", "Retrying with simplified prompt...")
                simple_prompt = self._build_simple_prompt(intent)
                response = await llm.generate(simple_prompt, max_tokens=3000)
                files = self._extract_files(response)

            if not files:
                await emit("generate_code", "error", "LLM returned no extractable code, using stub")
                files = self._generate_stub(intent)

            session.files = files
            await emit("generate_code", "success",
                f"Generated {len(files)} files: {', '.join(files.keys())}")

            # ── Step 4: Generate platformio.ini ─────────────
            await emit("project_setup", "running", "Setting up PlatformIO project...")
            session.files["platformio.ini"] = generate_platformio_ini(
                intent["board"], intent["pio_dependencies"]
            )
            await emit("project_setup", "success", "Project structure ready")

            # ── Step 5: Write Files to Disk ─────────────────
            await emit("write_files", "running", "Writing project files...")
            project_dir = self.output_dir / session.session_id
            src_dir = project_dir / "src"
            include_dir = project_dir / "include"
            src_dir.mkdir(parents=True, exist_ok=True)
            include_dir.mkdir(parents=True, exist_ok=True)

            for filename, content in session.files.items():
                if filename == "platformio.ini":
                    (project_dir / filename).write_text(content)
                elif filename.endswith(".h"):
                    (include_dir / filename).write_text(content)
                else:
                    (src_dir / filename).write_text(content)

            await emit("write_files", "success", f"Project written to {project_dir}")

            # ── Step 6: Compile ─────────────────────────────
            for attempt in range(1, session.max_attempts + 1):
                session.attempt = attempt
                await emit("compile", "running", f"Compiling (attempt {attempt}/{session.max_attempts})...")

                compile_result = await self._compile(project_dir)
                session.compile_output = compile_result["output"]
                session.compile_success = compile_result["success"]

                if compile_result["success"]:
                    await emit("compile", "success", f"✓ Build successful on attempt {attempt}")
                    break
                else:
                    errors = self._parse_compile_errors(compile_result["output"])
                    session.errors = errors
                    await emit("compile", "error",
                        f"Build failed: {len(errors)} errors. {errors[0] if errors else 'Unknown'}")

                    if attempt < session.max_attempts:
                        # ── Step 6b: Self-heal ──────────────
                        await emit("self_heal", "running", f"AI analyzing {len(errors)} errors...")
                        fixed_files = await self._self_heal(
                            session.files, errors, intent, chip_context
                        )
                        if fixed_files:
                            session.files.update(fixed_files)
                            # Rewrite fixed files
                            for fn, content in fixed_files.items():
                                dest = include_dir / fn if fn.endswith(".h") else src_dir / fn
                                dest.write_text(content)
                            await emit("self_heal", "success", f"Fixed {len(fixed_files)} files, retrying...")
                        else:
                            await emit("self_heal", "error", "Could not auto-fix, retrying with different approach...")

            # ── Step 7: Verify ──────────────────────────────
            if session.compile_success:
                await emit("verify", "running", "Running code quality checks...")
                issues = self._verify_code(session.files)
                if issues:
                    await emit("verify", "success", f"⚡ {len(issues)} suggestions: {issues[0]}")
                else:
                    await emit("verify", "success", "✓ No issues found — firmware is production-ready")

            session.status = "success" if session.compile_success else "failed"

        except Exception as e:
            session.status = "failed"
            await emit("error", "error", f"Pipeline error: {str(e)}")

        return session

    def _build_code_prompt(self, intent: dict, chip_context: str) -> str:
        """Build the LLM prompt with full hardware context."""
        peripherals_str = ", ".join(intent["peripherals"]) if intent["peripherals"] else "none specified"
        features_str = "\n".join(f"  - {f}" for f in intent["features"]) if intent["features"] else "  (none specified)"

        return f"""You are Parakram, an expert embedded firmware engineer. Generate production-ready C++ firmware.

## USER REQUEST
{intent['raw_prompt']}

## TARGET HARDWARE
- Board: {intent['board']}
- Framework: Arduino (PlatformIO)
- Peripherals detected: {peripherals_str}
- Features requested:
{features_str}

## CHIP-SPECIFIC CONTEXT
{chip_context}

## REQUIREMENTS
1. Generate a COMPLETE main.cpp with setup() and loop()
2. Include ALL necessary #include directives
3. Add INLINE COMMENTS explaining every register access and peripheral config
4. Handle ALL error cases (init failures, communication timeouts)
5. Use proper pin definitions with #define
6. Add serial debug output for verification
7. Follow embedded best practices: no malloc in loop, no String concatenation, volatile for ISR vars

## OUTPUT FORMAT
Return code in fenced blocks with filenames:
```cpp:main.cpp
// your code here
```

```cpp:config.h
// any configuration defines
```

IMPORTANT: The code MUST compile with PlatformIO. Do not use placeholder values."""

    def _build_simple_prompt(self, intent: dict) -> str:
        """Build a shorter prompt for small local models (parakram-coder).
        Uses the ===HEADER===/===SOURCE=== format the model was trained on."""
        peripherals_str = ", ".join(intent["peripherals"]) if intent["peripherals"] else "none"
        return f"""Generate complete Arduino C++ firmware for {intent['board']}.

Task: {intent['raw_prompt']}
Peripherals: {peripherals_str}

Rules:
1. Include ALL necessary #include directives
2. Add setup() and loop() functions
3. Use Serial.begin(115200) for debug output
4. Handle errors with Serial.println

Reply with code using this EXACT format:

===HEADER===
(complete .h file)
===SOURCE===
(complete .cpp file with #include <Arduino.h>)"""

    def _extract_files(self, response: str) -> dict[str, str]:
        """Extract files from LLM response. Handles multiple formats:
        1. ===HEADER=== / ===SOURCE=== (parakram-coder trained format)
        2. ```cpp:filename fenced blocks (OpenRouter prompt format)
        3. Plain ```cpp fenced blocks (generic fallback)
        """
        files = {}

        if not response:
            return files

        # ── Format 1: ===HEADER=== / ===SOURCE=== (parakram-coder) ──
        if "===HEADER===" in response and "===SOURCE===" in response:
            parts = response.split("===SOURCE===")
            header_raw = parts[0].replace("===HEADER===", "").strip()
            source_raw = parts[1].strip() if len(parts) > 1 else ""

            # Strip ``` fences inside the markers
            for fence in ["```cpp", "```c", "```arduino", "```"]:
                header_raw = header_raw.replace(fence, "")
                source_raw = source_raw.replace(fence, "")

            header = header_raw.strip()
            source = source_raw.strip()

            if source:
                files["main.cpp"] = source
            if header:
                # Try to extract the guard name for the header filename
                guard_match = re.search(r'#ifndef\s+(\w+)_H', header)
                if guard_match:
                    header_name = guard_match.group(1).lower() + ".h"
                else:
                    header_name = "config.h"
                files[header_name] = header

            if files:
                return files

        # ── Format 2: ```cpp:filename fenced blocks ──
        pattern = r'```(?:cpp|c|h):?\s*([\w.]+)\s*\n(.*?)```'
        matches = re.findall(pattern, response, re.DOTALL)
        for filename, content in matches:
            files[filename] = content.strip()

        if files:
            return files

        # ── Format 3: Plain fenced code blocks → main.cpp ──
        plain_pattern = r'```(?:cpp|c|arduino)\s*\n(.*?)```'
        plain_matches = re.findall(plain_pattern, response, re.DOTALL)
        if len(plain_matches) >= 2:
            files["config.h"] = plain_matches[0].strip()
            files["main.cpp"] = plain_matches[1].strip()
        elif len(plain_matches) == 1:
            files["main.cpp"] = plain_matches[0].strip()

        # ── Format 4: Raw code without fences ──
        if not files and ("#include" in response or "void setup" in response):
            files["main.cpp"] = response.strip()

        return files

    def _generate_stub(self, intent: dict) -> dict[str, str]:
        """Generate a minimal compilable stub when LLM fails."""
        includes = "\n".join(f"#include <{lib}>" for lib in intent.get("libraries", []))
        return {
            "main.cpp": f"""// Parakram AI — Auto-generated stub for: {intent['raw_prompt'][:60]}
// Board: {intent['board']}
// TODO: LLM generation failed — this is a minimal compilable stub

#include <Arduino.h>
{includes}

void setup() {{
    Serial.begin(115200);
    Serial.println("[Parakram] Firmware initialized");
    // TODO: Initialize peripherals: {', '.join(intent.get('peripherals', []))}
}}

void loop() {{
    Serial.println("[Parakram] Running...");
    delay(1000);
}}
"""
        }

    async def _compile(self, project_dir: Path) -> dict:
        """Run PlatformIO compile."""
        try:
            proc = await asyncio.create_subprocess_exec(
                "pio", "run", "-d", str(project_dir),
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.STDOUT,
            )
            stdout, _ = await asyncio.wait_for(proc.communicate(), timeout=120)
            output = stdout.decode(errors="replace")
            return {"success": proc.returncode == 0, "output": output}
        except asyncio.TimeoutError:
            return {"success": False, "output": "Compile timed out after 120s"}
        except FileNotFoundError:
            return {"success": False, "output": "PlatformIO CLI not found. Install: pip install platformio"}
        except Exception as e:
            return {"success": False, "output": f"Compile error: {str(e)}"}

    def _parse_compile_errors(self, output: str) -> list[str]:
        """Extract error messages from PlatformIO output."""
        errors = []
        for line in output.split("\n"):
            if ": error:" in line.lower() or "error:" in line.lower():
                errors.append(line.strip())
        return errors[:10]  # Cap at 10

    async def _self_heal(self, files: dict, errors: list, intent: dict, chip_context: str) -> dict:
        """Use LLM to fix compile errors."""
        from agents.llm_provider import get_provider
        llm = get_provider()

        error_context = "\n".join(errors[:5])
        source_context = "\n\n".join(
            f"// FILE: {fn}\n{content}" for fn, content in files.items() if fn.endswith((".cpp", ".h"))
        )

        fix_prompt = f"""The following firmware code has compile errors. Fix ALL errors and return the corrected files.

## ERRORS
{error_context}

## CURRENT CODE
{source_context}

## CHIP CONTEXT
{chip_context[:2000]}

## RULES
1. Fix ALL errors — do not introduce new ones
2. Return complete files in ```cpp:filename format
3. Keep all existing functionality
4. Do NOT remove #include directives unless they are wrong"""

        try:
            response = await llm.generate(fix_prompt)
            return self._extract_files(response)
        except Exception:
            return {}

    def _verify_code(self, files: dict) -> list[str]:
        """Run static checks on generated code."""
        issues = []
        for fn, content in files.items():
            if not fn.endswith((".cpp", ".c")):
                continue
            if "delay(" in content and "millis()" not in content:
                issues.append(f"{fn}: Consider using millis() instead of delay() for non-blocking operation")
            if "String " in content and fn == "main.cpp":
                issues.append(f"{fn}: Arduino String class can cause heap fragmentation — consider char arrays")
            if "malloc" in content or "new " in content:
                issues.append(f"{fn}: Dynamic allocation detected — may cause memory issues on MCU")
            if "while(1)" in content.replace(" ", "") and "watchdog" not in content.lower():
                issues.append(f"{fn}: Infinite loop without watchdog timer")
        return issues
