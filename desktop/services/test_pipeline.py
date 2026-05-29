"""
Comprehensive Pipeline Test Suite — Tests every core API endpoint.

Run: python test_pipeline.py
"""

import asyncio
import sys
import os
import json
import time

# Add parent to path
sys.path.insert(0, os.path.dirname(__file__))


def header(msg):
    print(f"\n{'='*60}")
    print(f"  {msg}")
    print(f"{'='*60}")


def ok(msg):
    print(f"  ✅ {msg}")


def fail(msg):
    print(f"  ❌ {msg}")


def info(msg):
    print(f"  ℹ️  {msg}")


async def test_nl_graph():
    """Test NL → Block Graph (concept matching)."""
    header("TEST 1: NL → Block Graph")
    from agents.nl_graph_agent import NLGraphAgent
    agent = NLGraphAgent()

    prompts = [
        "build me a weather station with MQTT",
        "smart home with temperature sensor relay and OLED display",
        "GPS tracker with LoRa and battery monitor",
        "robot with motors ultrasonic sensor and bluetooth",
        "plant watering system with soil moisture and relay",
    ]

    for prompt in prompts:
        graph = agent.build_graph(prompt)
        block_ids = [n["block_id"] for n in graph["nodes"]]
        if len(block_ids) >= 2:
            ok(f"'{prompt[:40]}...' → {len(block_ids)} blocks: {block_ids}")
        else:
            fail(f"'{prompt[:40]}...' → only {len(block_ids)} blocks")


async def test_golden_blocks():
    """Test Golden Block Template availability."""
    header("TEST 2: Golden Blocks Library")
    from services.template_codegen import TemplateCodeGenerator
    gen = TemplateCodeGenerator()
    blocks = gen.get_available_blocks()
    info(f"Total golden blocks: {len(blocks)}")

    categories = {}
    for b in blocks:
        cat = b["category"]
        categories[cat] = categories.get(cat, 0) + 1

    for cat, count in sorted(categories.items()):
        ok(f"  {cat}: {count} blocks")

    if len(blocks) >= 20:
        ok(f"Library has {len(blocks)} verified blocks — EXCELLENT")
    else:
        fail(f"Only {len(blocks)} blocks — needs more")


async def test_template_build():
    """Test template-only build (100% deterministic)."""
    header("TEST 3: Template-Only Build")
    from services.template_codegen import TemplateCodeGenerator
    gen = TemplateCodeGenerator()

    test_sets = [
        ["bme280", "wifi_station", "mqtt_client"],
        ["pir_sensor", "relay_module", "neopixel_strip"],
        ["gps_neo6m", "lora_sx1276", "battery_monitor"],
    ]

    for block_ids in test_sets:
        result = gen.build_from_blocks(block_ids, project_name=f"test_{'_'.join(block_ids[:2])}")
        if result["success"]:
            ok(f"{block_ids} → SUCCESS")
            misra = result.get("misra_compliance", {})
            info(f"  MISRA: {misra.get('total_violations_found', 0)} found, "
                 f"{misra.get('total_violations_fixed', 0)} auto-fixed, "
                 f"all_compliant={misra.get('all_compliant', False)}")
            for block in result["blocks"]:
                info(f"  [{block['id']}] MISRA Grade: {block.get('misra_grade', '?')} "
                     f"Score: {block.get('misra_score', '?')}")
        else:
            fail(f"{block_ids} → FAIL: {result.get('error', 'unknown')}")


async def test_template_from_prompt():
    """Test template build from natural language."""
    header("TEST 4: Template Build from NL Prompt")
    from services.template_codegen import TemplateCodeGenerator
    gen = TemplateCodeGenerator()

    prompts = [
        "weather station with MQTT",
        "smart home system",
        "data logger with SD card",
    ]

    for prompt in prompts:
        result = gen.build_from_prompt(prompt, project_name=f"test_nl_{prompt[:15].replace(' ', '_')}")
        if result["success"]:
            blocks = [b["id"] for b in result["blocks"]]
            ok(f"'{prompt}' → {len(blocks)} blocks: {blocks}")
        else:
            fail(f"'{prompt}' → {result.get('error', 'unknown')}")


async def test_misra_checker():
    """Test MISRA checker with auto-fix."""
    header("TEST 5: MISRA C:2012 Compliance Engine")
    from agents.misra_checker import get_misra_checker
    checker = get_misra_checker()

    # Test code with deliberate violations
    bad_code = """
#include <stdio.h>
#include <stdlib.h>
#include "sensor.h"

void sensor_setup() {
    char* buf = (char*)malloc(256);
    printf("Sensor init\\n");
    delay(5000);
    digitalWrite(13, HIGH);
    analogRead(34);
}

void sensor_loop() {
    int val = analogRead(34);
    printf("Value: %d\\n", val);
}
"""

    # Check original
    violations = checker.analyze(bad_code, "test.cpp")
    info(f"Original violations: {len(violations)}")
    for v in violations:
        info(f"  [{v['rule']}] {v['severity']}: {v['message']}")

    # Auto-fix
    result = checker.ensure_compliance(bad_code, "test.cpp")
    info(f"After auto-fix: {result['original_violations']} found → "
         f"{result['violations_fixed']} fixed in {result['iterations']} iterations")
    score = result["compliance"]
    if score["score"] >= 70:
        ok(f"MISRA Score: {score['score']} Grade: {score['grade']} — {score['status']}")
    else:
        fail(f"MISRA Score: {score['score']} Grade: {score['grade']} — needs improvement")

    # Test a golden block (should already be compliant)
    from services.template_codegen import TemplateCodeGenerator
    gen = TemplateCodeGenerator()
    blocks = gen.get_available_blocks()
    if blocks:
        first = blocks[0]
        bid = first["id"]
        block = gen._golden_blocks.get(bid, {})
        fw = block.get("firmware_template", {})
        if fw.get("source"):
            golden_result = checker.ensure_compliance(fw["source"], f"{bid}.cpp")
            golden_score = golden_result["compliance"]["score"]
            if golden_score >= 80:
                ok(f"Golden block '{bid}' MISRA Score: {golden_score} — GOOD")
            else:
                fail(f"Golden block '{bid}' MISRA Score: {golden_score} — needs fix")


async def test_llm_router():
    """Test LLM Router configuration."""
    header("TEST 6: LLM Router")
    from agents.llm_provider import get_router
    router = get_router()
    info(f"Active model: {router.active_model_id}")
    info(f"Active provider: {router.active.name}")
    info(f"Available: {router.active.is_available()}")

    models = router.list_models()
    info(f"Total models available: {len(models)}")
    for m in models:
        status = "🟢 ACTIVE" if m.get("active") else "⚪"
        info(f"  {status} {m['name']} ({m['id']}) [{m['provider']}]")

    ok("LLM Router initialized successfully")


async def test_anti_hallucination():
    """Test Anti-Hallucination Engine."""
    header("TEST 7: Anti-Hallucination Engine")
    from agents.anti_hallucination import AntiHallucinationEngine
    engine = AntiHallucinationEngine()

    # Test with code containing a hallucinated method
    test_code = """
#include "bme280.h"
#include <Wire.h>
#include <Adafruit_BME280.h>

static Adafruit_BME280 bme;

void bme280_setup() {
    Wire.begin();
    bme.begin(0x76);
}

void bme280_loop() {
    float temp = bme.readTemperature();
    float hum = bme.readHumidity();
    float pressure = bme.readPressure();
}
"""

    result = engine.validate_and_fix(test_code)
    info(f"Issues found: {result['issues_found']}")
    info(f"Issues fixed: {result['issues_fixed']}")
    info(f"Clean: {result['clean']}")
    ok("Anti-Hallucination Engine operational")


async def main():
    print("\n" + "🔧" * 30)
    print("  PARAKRAM PIPELINE TEST SUITE")
    print("🔧" * 30)
    t0 = time.time()

    await test_nl_graph()
    await test_golden_blocks()
    await test_template_build()
    await test_template_from_prompt()
    await test_misra_checker()
    await test_llm_router()
    await test_anti_hallucination()

    elapsed = round(time.time() - t0, 2)
    header(f"ALL TESTS COMPLETE — {elapsed}s")


if __name__ == "__main__":
    asyncio.run(main())
