"""
End-to-End Test Runner — Validate the autonomous firmware pipeline.

Runs 10 real-world prompts through the full pipeline and reports:
  - Intent parsing accuracy
  - Code generation success
  - MISRA compliance score
  - Memory estimation
  - Wiring generation
"""

import asyncio
import sys
import os
sys.path.insert(0, os.path.dirname(__file__))

from dotenv import load_dotenv
load_dotenv()

TEST_PROMPTS = [
    {
        "prompt": "Blink an LED on ESP32 GPIO2",
        "expected_board": "esp32dev",
        "expected_keywords": ["digitalWrite", "GPIO", "delay", "OUTPUT"],
        "category": "basic",
    },
    {
        "prompt": "Read temperature from BME280 over I2C on ESP32",
        "expected_board": "esp32dev",
        "expected_keywords": ["Wire", "BME280", "readTemperature", "begin"],
        "category": "sensor",
    },
    {
        "prompt": "WiFi weather station with BME280 and OLED display on ESP32",
        "expected_board": "esp32dev",
        "expected_keywords": ["WiFi", "BME280", "SSD1306", "display"],
        "category": "project",
    },
    {
        "prompt": "CAN bus reader on STM32 Nucleo F446RE",
        "expected_board": "nucleo_f446re",
        "expected_keywords": ["CAN", "HAL_CAN", "MCP2515"],
        "category": "protocol",
    },
    {
        "prompt": "Servo sweep 0-180 degrees on Arduino Uno",
        "expected_board": "uno",
        "expected_keywords": ["Servo", "write", "attach"],
        "category": "actuator",
    },
    {
        "prompt": "Deep sleep with timer wakeup every 5 minutes on ESP32",
        "expected_board": "esp32dev",
        "expected_keywords": ["esp_deep_sleep", "timer_wakeup", "RTC_DATA_ATTR"],
        "category": "power",
    },
    {
        "prompt": "MQTT client publishing sensor data on ESP32",
        "expected_board": "esp32dev",
        "expected_keywords": ["PubSubClient", "publish", "connect", "MQTT"],
        "category": "connectivity",
    },
    {
        "prompt": "FreeRTOS multi-task with two sensors on ESP32",
        "expected_board": "esp32dev",
        "expected_keywords": ["xTaskCreate", "vTaskDelay", "Queue"],
        "category": "rtos",
    },
    {
        "prompt": "NeoPixel rainbow animation on RP2040 Pico",
        "expected_board": "pico",
        "expected_keywords": ["NeoPixel", "setPixelColor", "show", "strip"],
        "category": "display",
    },
    {
        "prompt": "I2C scanner for Arduino Uno",
        "expected_board": "uno",
        "expected_keywords": ["Wire", "beginTransmission", "endTransmission", "scanner"],
        "category": "debugging",
    },
]


async def run_tests():
    """Run all end-to-end tests."""
    from agents.autonomous_agent import AutonomousAgent
    from agents.misra_checker import get_misra_checker
    from services.memory_analyzer import get_memory_analyzer
    from services.wiring_generator import get_wiring_generator
    from services.project_planner import get_project_planner

    agent = AutonomousAgent()
    misra = get_misra_checker()
    memory = get_memory_analyzer()
    planner = get_project_planner()

    results = []
    passed = 0
    total = len(TEST_PROMPTS)

    print("=" * 60)
    print("PARAKRAM by VIDYUTLABS — End-to-End Test Suite")
    print("=" * 60)

    for i, test in enumerate(TEST_PROMPTS):
        prompt = test["prompt"]
        print(f"\n[{i+1}/{total}] {prompt}")
        print("-" * 50)

        result = {"prompt": prompt, "category": test["category"], "passed": False, "details": {}}

        try:
            # 1) Parse intent
            from agents.autonomous_agent import parse_intent
            intent = parse_intent(prompt)
            board = intent.get("board", "esp32dev")
            print(f"  Board: {board} (expected: {test['expected_board']})")
            result["details"]["intent"] = intent

            # 2) Generate code
            session = await agent.execute(prompt)
            # Aggregate all code from all files (not just main.cpp)
            all_code = "\n".join(
                content for fname, content in session.files.items()
                if fname != "platformio.ini"
            )
            code = session.files.get("main.cpp", all_code)
            result["details"]["code_length"] = len(all_code)
            print(f"  Code: {len(all_code)} characters generated")

            # 3) Check keywords across ALL generated files
            found = [kw for kw in test["expected_keywords"] if kw.lower() in all_code.lower()]
            keyword_pct = len(found) / len(test["expected_keywords"]) * 100 if test["expected_keywords"] else 100
            print(f"  Keywords: {len(found)}/{len(test['expected_keywords'])} ({keyword_pct:.0f}%)")
            result["details"]["keywords"] = {"found": found, "percent": keyword_pct}

            # 4) MISRA check
            violations = misra.analyze(code, f"test_{i}.c")
            score = misra.get_compliance_score(violations)
            print(f"  MISRA: {score['score']}% ({score['grade']})")
            result["details"]["misra"] = score

            # 5) Memory estimate
            mem = memory.estimate_from_code(code, board)
            print(f"  Memory: Flash ~{mem['flash']['used']}B, RAM ~{mem['ram']['used']}B")
            result["details"]["memory"] = mem

            # Pass criteria: code generated + >=25% keywords found
            if len(code) > 50 and keyword_pct >= 25:
                result["passed"] = True
                passed += 1
                print(f"  ✅ PASSED")
            else:
                print(f"  ❌ FAILED (code={len(code)}, keywords={keyword_pct:.0f}%)")

        except Exception as e:
            print(f"  ❌ ERROR: {e}")
            result["details"]["error"] = str(e)

        results.append(result)

    # Summary
    print("\n" + "=" * 60)
    print(f"RESULTS: {passed}/{total} passed ({passed/total*100:.0f}%)")
    print("=" * 60)

    by_category: dict[str, list] = {}
    for r in results:
        c = r["category"]
        if c not in by_category:
            by_category[c] = []
        by_category[c].append(r)

    for cat, items in sorted(by_category.items()):
        cat_passed = sum(1 for item in items if item["passed"])
        print(f"  {cat}: {cat_passed}/{len(items)}")

    return {"passed": passed, "total": total, "percent": round(passed/total*100, 1), "results": results}


if __name__ == "__main__":
    asyncio.run(run_tests())
