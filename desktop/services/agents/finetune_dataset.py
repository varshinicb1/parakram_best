"""
Fine-Tuning Dataset Generator — creates training data from hardware library.

Generates:
1. JSONL instruction/response pairs for LoRA training
2. Ollama Modelfile with ESP32 system prompt
3. Conversation-format training data for chat models

Uses all 43 hardware library block definitions as source material.
"""

import os
import json
from datetime import datetime


HARDWARE_LIB_DIR = os.path.join(os.path.dirname(__file__), "..", "hardware_library")
OUTPUT_DIR = os.path.join(os.path.dirname(__file__), "..", "training_data")


def generate_dataset() -> dict:
    """
    Generate a JSONL training dataset from all hardware library templates.

    Returns:
        {
            "status": "success",
            "files": [list of generated file paths],
            "stats": {total_pairs, categories, ...}
        }
    """
    os.makedirs(OUTPUT_DIR, exist_ok=True)

    # Load all block definitions
    blocks = _load_all_blocks()
    print(f"[FineTune] Loaded {len(blocks)} block definitions")

    # Generate training pairs
    pairs = []
    for block in blocks:
        fw = block.get("firmware_template", {})
        if not fw.get("header") or not fw.get("source"):
            continue

        # ── Pair 1: Full module generation ──────────────
        instruction = _build_generation_instruction(block)
        response = f"===HEADER===\n{fw['header']}\n===SOURCE===\n{fw['source']}"
        pairs.append({
            "instruction": instruction,
            "response": response,
            "category": block.get("category", "unknown"),
            "block_id": block.get("id", "unknown"),
        })

        # ── Pair 2: Config-specific generation ──────────
        config = block.get("configuration", [])
        if config:
            custom_config = _generate_custom_config(config)
            custom_instruction = _build_generation_instruction(block, custom_config)
            pairs.append({
                "instruction": custom_instruction,
                "response": response,  # Same template, different config
                "category": block.get("category", "unknown"),
                "block_id": block.get("id", "unknown") + "_custom",
            })

        # ── Pair 3: Explanation / documentation ─────────
        pairs.append({
            "instruction": f"Explain how the {block.get('name', '')} module works in an ESP32 Arduino project. What libraries does it need? What are its inputs and outputs?",
            "response": _build_explanation(block),
            "category": block.get("category", "unknown"),
            "block_id": block.get("id", "unknown") + "_explain",
        })

    # Write JSONL (instruction tuning format)
    jsonl_path = os.path.join(OUTPUT_DIR, "firmware_training.jsonl")
    with open(jsonl_path, "w", encoding="utf-8") as f:
        for pair in pairs:
            json_line = {
                "messages": [
                    {"role": "system", "content": _system_prompt()},
                    {"role": "user", "content": pair["instruction"]},
                    {"role": "assistant", "content": pair["response"]},
                ]
            }
            f.write(json.dumps(json_line, ensure_ascii=False) + "\n")

    # Write Ollama Modelfile
    modelfile_path = os.path.join(OUTPUT_DIR, "Modelfile")
    with open(modelfile_path, "w", encoding="utf-8") as f:
        f.write(_generate_modelfile())

    # Write summary
    categories = set(p["category"] for p in pairs)
    stats = {
        "total_pairs": len(pairs),
        "blocks_with_templates": len([b for b in blocks if b.get("firmware_template", {}).get("source")]),
        "categories": sorted(categories),
        "generated_at": datetime.now().isoformat(),
    }

    stats_path = os.path.join(OUTPUT_DIR, "dataset_stats.json")
    with open(stats_path, "w", encoding="utf-8") as f:
        json.dump(stats, f, indent=2)

    print(f"[FineTune] Generated {len(pairs)} training pairs")
    print(f"[FineTune] Output: {OUTPUT_DIR}")

    return {
        "status": "success",
        "files": [jsonl_path, modelfile_path, stats_path],
        "stats": stats,
    }


def _load_all_blocks() -> list[dict]:
    """Load all hardware library JSON definitions."""
    blocks = []
    categories = [
        "sensors", "communication", "actuators", "audio",
        "display", "security", "freertos", "control_blocks",
    ]

    for category in categories:
        cat_dir = os.path.join(HARDWARE_LIB_DIR, category)
        if not os.path.isdir(cat_dir):
            continue
        for fname in sorted(os.listdir(cat_dir)):
            if not fname.endswith(".json"):
                continue
            try:
                with open(os.path.join(cat_dir, fname), "r", encoding="utf-8") as f:
                    blocks.append(json.load(f))
            except Exception as e:
                print(f"[FineTune] Error loading {fname}: {e}")
    return blocks


def _build_generation_instruction(block: dict, custom_config: dict = None) -> str:
    """Build a firmware generation instruction from a block definition."""
    name = block.get("name", "Unknown")
    category = block.get("category", "unknown")
    description = block.get("description", "")
    inputs = block.get("inputs", [])
    outputs = block.get("outputs", [])
    config = block.get("configuration", [])
    libs = block.get("libraries", [])

    config_text = ""
    if custom_config:
        config_text = f"\nConfiguration: {json.dumps(custom_config, indent=2)}"
    elif config:
        default_config = {c["key"]: c.get("default", "") for c in config}
        config_text = f"\nConfiguration: {json.dumps(default_config, indent=2)}"

    io_text = ""
    if inputs:
        io_text += "\nInputs: " + ", ".join(f"{p['name']}({p.get('data_type', '')})" for p in inputs)
    if outputs:
        io_text += "\nOutputs: " + ", ".join(f"{p['name']}({p.get('data_type', '')})" for p in outputs)

    libs_text = f"\nRequired libraries: {', '.join(libs)}" if libs else ""

    return f"""Generate Arduino firmware module for ESP32.

Block: {name}
Category: {category}
Description: {description}{io_text}{config_text}{libs_text}

Generate a complete .h header file and .cpp source file.
Use ===HEADER=== and ===SOURCE=== markers to separate them."""


def _generate_custom_config(config: list[dict]) -> dict:
    """Generate a plausible custom configuration (different from defaults)."""
    custom = {}
    for c in config:
        key = c.get("key", "")
        default = c.get("default", "")
        vtype = c.get("value_type", "string")

        if vtype == "int":
            try:
                val = int(default)
                custom[key] = str(val + 1)  # Slightly different
            except (ValueError, TypeError):
                custom[key] = default
        elif "pin" in key.lower():
            try:
                custom[key] = str(int(default) + 2)
            except (ValueError, TypeError):
                custom[key] = default
        elif "address" in key.lower():
            # Alternate I2C address
            if default == "0x76":
                custom[key] = "0x77"
            elif default == "0x68":
                custom[key] = "0x69"
            else:
                custom[key] = default
        else:
            custom[key] = default

    return custom


def _build_explanation(block: dict) -> str:
    """Build a natural language explanation of a block."""
    name = block.get("name", "Unknown")
    description = block.get("description", "")
    category = block.get("category", "unknown")
    libs = block.get("libraries", [])
    inputs = block.get("inputs", [])
    outputs = block.get("outputs", [])
    config = block.get("configuration", [])

    parts = [
        f"The {name} module is a {category} component for ESP32.",
        f"Description: {description}" if description else "",
    ]

    if libs:
        parts.append(f"Required libraries: {', '.join(libs)}.")

    if outputs:
        out_desc = ", ".join(f"{o['name']} ({o.get('data_type', 'unknown')})" for o in outputs)
        parts.append(f"Outputs: {out_desc}.")

    if inputs:
        in_desc = ", ".join(f"{i['name']} ({i.get('data_type', 'unknown')})" for i in inputs)
        parts.append(f"Inputs: {in_desc}.")

    if config:
        cfg_desc = ", ".join(f"{c['key']}={c.get('default', 'N/A')}" for c in config)
        parts.append(f"Default configuration: {cfg_desc}.")

    parts.append(f"It provides {name.lower()}_setup() for initialization and {name.lower()}_loop() for the main read/write cycle.")

    return " ".join(p for p in parts if p)


def _system_prompt() -> str:
    """ESP32 firmware generation system prompt."""
    return """You are an expert ESP32 firmware engineer specializing in Arduino framework development.

Rules:
1. Generate ONLY valid, compilable C++ code for ESP32 Arduino
2. Use proper #include guards in headers (#ifndef / #define / #endif)
3. Prefix all functions with the module name (e.g., bme280_setup, bme280_loop)
4. Always include error handling and Serial debug output
5. Use static variables for module state (avoid globals)
6. Initialize hardware with retry logic where applicable
7. Include proper library #includes
8. Respond with ===HEADER=== and ===SOURCE=== markers"""


def _generate_modelfile() -> str:
    """Generate an Ollama Modelfile for creating a custom firmware model."""
    return f"""# Parakram AI — ESP32 Firmware Generation Model
# Created: {datetime.now().isoformat()}
#
# Usage:
#   ollama create parakram-coder -f Modelfile
#
# This creates a custom model based on qwen2.5-coder with ESP32-specific
# system prompt and optimized parameters for firmware generation.

FROM qwen2.5-coder:7b-instruct

SYSTEM \"\"\"You are Parakram AI, an expert ESP32 firmware engineer.

You generate modular Arduino framework code for the ESP32 microcontroller.
Each module consists of a .h header file and a .cpp source file.

Code guidelines:
- Always use #include guards (#ifndef / #define / #endif)
- Prefix all functions with the module name (e.g., bme280_setup, bme280_loop)
- Use static variables for module-level state
- Include error handling with Serial debug output
- Use retry logic for hardware initialization (I2C, SPI sensors)
- Support standard Arduino/ESP32 libraries (Wire, SPI, WiFi, etc.)
- Include sanity checks for sensor readings

Response format:
===HEADER===
(complete .h file)
===SOURCE===
(complete .cpp file)
\"\"\"

PARAMETER temperature 0.2
PARAMETER top_p 0.9
PARAMETER top_k 40
PARAMETER num_predict 3000
PARAMETER repeat_penalty 1.1
"""


if __name__ == "__main__":
    result = generate_dataset()
    print(f"\nGenerated {result['stats']['total_pairs']} training pairs")
    print(f"Files: {result['files']}")
