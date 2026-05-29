"""
Enhanced Firmware Agent — Ollama-powered with RAG context injection.

Pipeline:
1. Check hardware library for existing firmware_template (exact match)
2. If no exact match, query RAG engine for similar block templates
3. Build a context-rich prompt with similar examples
4. Generate via Ollama qwen2.5-coder:7b-instruct
5. Extract and validate code structure
6. Fall back to stub if generation fails
"""

import os
import json
from agents.llm_provider import get_provider
from agents.rag_engine import get_rag_engine
from agents.library_registry import get_libs_for_block, format_library_context, get_platformio_deps


HARDWARE_LIB_DIR = os.path.join(os.path.dirname(__file__), "..", "hardware_library")


class FirmwareAgent:
    """AI agent for generating firmware code per block using Ollama + RAG."""

    def __init__(self):
        self.llm = get_provider()
        self.rag = get_rag_engine()

    async def generate_block_code(
        self, node: dict, dependencies: list = None
    ) -> dict:
        """
        Generate .cpp and .h code for a single block.

        Strategy:
        1. Look up exact firmware_template from hardware library JSON
        2. If found, apply configuration overrides via Ollama
        3. If not found, use RAG to find similar templates as examples
        4. Generate code via Ollama with full context
        5. Fall back to stub on failure
        """
        name = node.name if hasattr(node, 'name') else str(node)
        category = node.category if hasattr(node, 'category') else 'unknown'
        description = node.description if hasattr(node, 'description') else ''
        configuration = node.configuration if hasattr(node, 'configuration') else {}
        safe_name = name.lower().replace(" ", "_").replace("-", "_")

        # ── Strategy 1: Exact template match ────────────────
        exact_template = self._load_exact_template(safe_name, category)
        if exact_template and exact_template.get("header") and exact_template.get("source"):
            print(f"[FirmwareAgent] Using exact template for '{name}'")
            # Apply config overrides via Ollama if config differs from defaults
            if configuration and self.llm.is_available():
                customized = await self._customize_template(
                    name, safe_name, category, description,
                    configuration, exact_template, dependencies
                )
                if customized.get("source"):
                    return customized
            return exact_template

        # ── Strategy 2: RAG-augmented generation ────────────
        if self.llm.is_available():
            print(f"[FirmwareAgent] RAG-augmented generation for '{name}'")
            return await self._rag_generate(
                name, safe_name, category, description,
                configuration, dependencies
            )

        # ── Strategy 3: Stub fallback ───────────────────────
        print(f"[FirmwareAgent] Falling back to stub for '{name}'")
        return self._generate_stub(name, safe_name)

    def _load_exact_template(self, safe_name: str, category: str) -> dict:
        """Try to load an exact firmware template from hardware library.
        
        Attempts multiple matching strategies:
        1. Direct filename match (safe_name.json)
        2. Block ID match from JSON content
        3. Name variant matching (strip common words, first word, etc.)
        """
        # Build list of name variants to try
        name_variants = [safe_name]
        
        # Strip common suffixes/prefixes that bloat names
        for strip in ["_sensor", "_module", "_controller", "_output", "_input", 
                       "_block", "_driver", "_board", "temperature_&_", "temperature_",
                       "_temperature", "_humidity"]:
            stripped = safe_name.replace(strip, "").strip("_")
            if stripped and stripped not in name_variants:
                name_variants.append(stripped)
        
        # Try first word (e.g., "dht22" from "dht22_temperature_&_humidity")
        first_word = safe_name.split("_")[0]
        if first_word and len(first_word) > 2 and first_word not in name_variants:
            name_variants.append(first_word)
        
        # Map categories to directories
        cat_dirs = {
            "sensor": "sensors", "communication": "communication",
            "actuator": "actuators", "audio": "audio",
            "display": "display", "security": "security",
            "freertos": "freertos", "logic": "control_blocks",
            "control": "control_blocks", "output": "actuators",
        }

        # Collect all category directories to search
        search_dirs = []
        if category in cat_dirs:
            search_dirs.append(cat_dirs[category])
        for d in cat_dirs.values():
            if d not in search_dirs:
                search_dirs.append(d)

        # Strategy 1: Try direct filename match with all name variants
        for cat_dir in search_dirs:
            dir_path = os.path.join(HARDWARE_LIB_DIR, cat_dir)
            if not os.path.isdir(dir_path):
                continue
            for variant in name_variants:
                json_path = os.path.join(dir_path, f"{variant}.json")
                if os.path.exists(json_path):
                    result = self._read_template(json_path)
                    if result:
                        return result

        # Strategy 2: Scan all .json files and match by "id" field
        for cat_dir in search_dirs:
            dir_path = os.path.join(HARDWARE_LIB_DIR, cat_dir)
            if not os.path.isdir(dir_path):
                continue
            for fname in os.listdir(dir_path):
                if not fname.endswith(".json"):
                    continue
                fpath = os.path.join(dir_path, fname)
                try:
                    with open(fpath, "r", encoding="utf-8") as f:
                        block = json.load(f)
                    block_id = block.get("id", "").lower()
                    # Match if block ID equals any name variant
                    if block_id and block_id in name_variants:
                        fw = block.get("firmware_template", {})
                        if fw and (fw.get("header") or fw.get("source")):
                            return {"header": fw.get("header", ""), "source": fw.get("source", "")}
                except Exception:
                    pass

        # Strategy 3: RAG engine exact match
        for variant in name_variants:
            rag_template = self.rag.get_template_by_id(variant)
            if rag_template and (rag_template.get("header") or rag_template.get("source")):
                return {"header": rag_template.get("header", ""), "source": rag_template.get("source", "")}

        return {}

    def _read_template(self, json_path: str) -> dict:
        """Read firmware template from a JSON file."""
        try:
            with open(json_path, "r", encoding="utf-8") as f:
                block = json.load(f)
            fw = block.get("firmware_template", {})
            if fw and (fw.get("header") or fw.get("source")):
                return {"header": fw.get("header", ""), "source": fw.get("source", "")}
        except Exception as e:
            print(f"[FirmwareAgent] Error loading template: {e}")
        return {}

    async def _customize_template(
        self, name: str, safe_name: str, category: str, description: str,
        configuration: dict, template: dict, dependencies: list
    ) -> dict:
        """Use Ollama to customize a template with user-specified configuration."""
        prompt = f"""You have an existing firmware template for the {name} ({category}) block.
The user has specific configuration that may require adjustments.

EXISTING TEMPLATE HEADER:
```cpp
{template['header']}
```

EXISTING TEMPLATE SOURCE:
```cpp
{template['source']}
```

USER CONFIGURATION:
{json.dumps(configuration, indent=2)}

DEPENDENCIES (upstream blocks): {dependencies or 'none'}

TASK: Modify the template to apply the user's configuration values.
For example, if the user set pin=17 instead of default pin=4, update the code.
If the user set i2c_address=0x77, update the address in the code.

Keep all existing error handling, retry logic, and structure intact.
Only modify the configuration-specific values.

Respond in this exact format:
===HEADER===
(complete modified .h file)
===SOURCE===
(complete modified .cpp file)
"""

        result = await self.llm.generate_code(prompt, max_tokens=3000)

        # If Ollama mangled it, fall back to original template
        if not result.get("source") or len(result["source"]) < 50:
            return template

        return result

    async def _rag_generate(
        self, name: str, safe_name: str, category: str, description: str,
        configuration: dict, dependencies: list
    ) -> dict:
        """Generate firmware using RAG context from similar blocks."""

        # Retrieve similar templates
        query = f"{name} {category} {description}"
        similar = await self.rag.retrieve(query, top_k=3)

        # Build context from similar templates
        context_blocks = []
        for i, match in enumerate(similar):
            fw = match.get("firmware_template", {})
            if fw.get("header") and fw.get("source"):
                context_blocks.append(
                    f"--- Example {i+1}: {match['name']} ({match['category']}) "
                    f"[similarity: {match['similarity']}] ---\n"
                    f"HEADER:\n```cpp\n{fw['header']}\n```\n"
                    f"SOURCE:\n```cpp\n{fw['source']}\n```"
                )

        # Limit context to avoid exceeding context window
        context_text = "\n\n".join(context_blocks[:2])  # Top 2 examples

        # Build IO description
        io_desc = ""
        if hasattr(dependencies, '__iter__') and dependencies:
            io_desc = f"\nDependencies (upstream blocks): {', '.join(str(d) for d in dependencies)}"

        # Look up actual library APIs to prevent hallucination
        block_meta = {"libraries": [], "name": name, "category": category}
        for doc in self.rag._documents:
            if doc.get("id") == safe_name or doc.get("metadata", {}).get("name") == name:
                block_meta["libraries"] = doc.get("metadata", {}).get("libraries", [])
                break
        # Also check similar blocks for library hints
        if not block_meta["libraries"] and similar:
            block_meta["libraries"] = similar[0].get("metadata", {}).get("libraries", [])

        lib_infos = get_libs_for_block(block_meta)
        lib_context = format_library_context(lib_infos)

        prompt = f"""Generate Arduino firmware for an ESP32 block module.

BLOCK SPECIFICATION:
- Name: {name}
- Category: {category}
- Description: {description}
- Configuration: {json.dumps(configuration, indent=2) if configuration else 'default'}
{io_desc}

{lib_context}

SIMILAR EXISTING MODULES (use these as style/pattern references):
{context_text if context_text else 'No similar modules found — generate from scratch.'}

REQUIREMENTS:
1. Header file (.h): #ifndef guard, function declarations
2. Source file (.cpp): Full implementation with:
   - {safe_name}_setup() — initialization with retry logic
   - {safe_name}_loop() — main loop logic
   - Getter functions for all outputs
   - Serial debug output with [{safe_name}] prefix
   - Error handling and sanity checks
3. ONLY use methods listed in the LIBRARY API REFERENCE above
4. Do NOT invent or hallucinate library methods that don't exist
5. Follow the patterns from the example modules above

Respond in this exact format:
===HEADER===
(complete .h file content)
===SOURCE===
(complete .cpp file content)
"""

        result = await self.llm.generate_code(prompt, max_tokens=3000)

        # Validate we got something useful
        if result.get("source") and len(result["source"]) > 50:
            return result

        # Failed — fall back to stub
        print(f"[FirmwareAgent] Ollama generation insufficient for '{name}', using stub")
        return self._generate_stub(name, safe_name)

    def _generate_stub(self, name: str, safe_name: str = None) -> dict:
        """Generate basic stub code when all else fails."""
        if safe_name is None:
            safe_name = name.lower().replace(" ", "_").replace("-", "_")

        guard = safe_name.upper() + "_H"

        header = f"""#ifndef {guard}
#define {guard}

#include <Arduino.h>

// {name} — stub (AI-generated code pending)
void {safe_name}_setup();
void {safe_name}_loop();

#endif // {guard}
"""

        source = f"""#include "{safe_name}.h"

// {name} — stub implementation
void {safe_name}_setup() {{
    Serial.println("[{safe_name}] Setup — stub");
}}

void {safe_name}_loop() {{
    // TODO: Implement {name} logic
}}
"""
        return {"header": header, "source": source}

    async def fix_compile_error(
        self, source_code: str, error_output: str
    ) -> str:
        """Use Ollama to fix a compilation error."""
        if not self.llm.is_available():
            return source_code

        prompt = f"""Fix this ESP32 Arduino code based on the compile error.

Source Code:
```cpp
{source_code}
```

Compile Error:
```
{error_output}
```

Return ONLY the fixed source code, no explanations. Do not include markdown fences."""

        try:
            fixed = await self.llm.generate(
                prompt, max_tokens=3000, temperature=0.1
            )
            if fixed and len(fixed) > 30:
                # Strip any accidental markdown fences
                for fence in ["```cpp", "```c", "```"]:
                    fixed = fixed.replace(fence, "")
                return fixed.strip()
            return source_code
        except Exception as e:
            print(f"[FirmwareAgent] Fix error failed: {e}")
            return source_code
