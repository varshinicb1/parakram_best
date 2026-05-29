"""
Firmware Generator Service
Converts canvas graph into modular firmware source files.
Each block generates its own .cpp/.h pair. main.cpp orchestrates all modules.
"""

import os
import json
from models.graph_model import CanvasGraph
from agents.firmware_agent import FirmwareAgent


class FirmwareGenerator:
    """Generates modular firmware from a canvas graph."""

    def __init__(self):
        self.firmware_agent = FirmwareAgent()
        self.projects_dir = os.environ.get("PROJECTS_DIR", "../projects")
        self.templates_dir = os.environ.get("TEMPLATES_DIR", "../firmware_templates")

    async def generate(self, project_id: str, canvas: CanvasGraph) -> list[str]:
        """
        Generate firmware files from canvas graph.

        Strategy:
        1. Analyze the graph to determine module dependencies
        2. Generate a .cpp/.h pair for each block node
        3. Generate main.cpp that initializes and loops all modules
        4. Generate platformio.ini with required libraries

        Returns list of generated file paths.
        """
        project_dir = os.path.join(self.projects_dir, project_id)
        firmware_dir = os.path.join(project_dir, "firmware")
        src_dir = os.path.join(firmware_dir, "src")
        include_dir = os.path.join(firmware_dir, "include")

        # Ensure directories exist
        os.makedirs(src_dir, exist_ok=True)
        os.makedirs(include_dir, exist_ok=True)

        generated_files = []

        # Build dependency graph from edges
        dependencies = self._build_dependency_map(canvas)

        # Generate module for each block node
        for node in canvas.nodes:
            module_files = await self._generate_block_module(
                node=node,
                dependencies=dependencies.get(node.id, []),
                src_dir=src_dir,
                include_dir=include_dir,
            )
            generated_files.extend(module_files)

        # Generate main.cpp
        main_file = self._generate_main(canvas, src_dir)
        generated_files.append(main_file)

        # Generate platformio.ini
        ini_file = self._generate_platformio_ini(canvas, firmware_dir)
        generated_files.append(ini_file)

        return generated_files

    def _build_dependency_map(self, canvas: CanvasGraph) -> dict:
        """Build a map of node_id -> list of upstream node IDs."""
        deps = {}
        for edge in canvas.edges:
            target = edge.target
            source = edge.source
            if target not in deps:
                deps[target] = []
            deps[target].append(source)
        return deps

    async def _generate_block_module(
        self, node, dependencies, src_dir, include_dir
    ) -> list[str]:
        """
        Generate .cpp and .h files for a single block.
        Uses AI agent for complex blocks, templates for standard ones.
        """
        safe_name = node.name.lower().replace(" ", "_")

        # Try template first, fall back to AI generation
        header_content = self._get_template_header(node, safe_name)
        source_content = self._get_template_source(node, safe_name, dependencies)

        # If no template available, use AI agent
        if not header_content or not source_content:
            ai_result = await self.firmware_agent.generate_block_code(
                node=node,
                dependencies=dependencies,
            )
            header_content = ai_result.get("header", header_content or "")
            source_content = ai_result.get("source", source_content or "")

        files = []

        # Write header
        header_path = os.path.join(include_dir, f"{safe_name}.h")
        with open(header_path, "w") as f:
            f.write(header_content)
        files.append(header_path)

        # Write source
        source_path = os.path.join(src_dir, f"block_{safe_name}.cpp")
        with open(source_path, "w") as f:
            f.write(source_content)
        files.append(source_path)

        return files

    def _get_template_header(self, node, safe_name: str) -> str:
        """Get header template for a block category."""
        guard = safe_name.upper() + "_H"
        return f"""#ifndef {guard}
#define {guard}

#include <Arduino.h>

// {node.name} — {node.description}
void {safe_name}_setup();
void {safe_name}_loop();

#endif // {guard}
"""

    def _get_template_source(self, node, safe_name: str, dependencies) -> str:
        """Get source template for a block category."""
        includes = [f'#include "{safe_name}.h"']
        for dep_id in dependencies:
            dep_name = dep_id.lower().replace(" ", "_")
            includes.append(f'#include "{dep_name}.h"')

        includes_str = "\n".join(includes)

        return f"""{includes_str}

// {node.name} — {node.description}
// Category: {node.category}

void {safe_name}_setup() {{
    // TODO: Initialize {node.name}
    Serial.println("[{safe_name}] Initialized");
}}

void {safe_name}_loop() {{
    // TODO: Main loop for {node.name}
}}
"""

    def _generate_main(self, canvas: CanvasGraph, src_dir: str) -> str:
        """Generate main.cpp that orchestrates all block modules."""
        includes = []
        setup_calls = []
        loop_calls = []

        for node in canvas.nodes:
            safe_name = node.name.lower().replace(" ", "_")
            includes.append(f'#include "{safe_name}.h"')
            setup_calls.append(f"    {safe_name}_setup();")
            loop_calls.append(f"    {safe_name}_loop();")

        content = f"""// Parakram AI — Auto-generated firmware
// Project nodes: {len(canvas.nodes)}
// Project edges: {len(canvas.edges)}

#include <Arduino.h>
{chr(10).join(includes)}

void setup() {{
    Serial.begin(115200);
    delay(1000);
    Serial.println("=== Parakram AI Firmware ===");
    Serial.println("Initializing modules...");

{chr(10).join(setup_calls)}

    Serial.println("All modules initialized.");
}}

void loop() {{
{chr(10).join(loop_calls)}
    delay(10);
}}
"""
        main_path = os.path.join(src_dir, "main.cpp")
        with open(main_path, "w") as f:
            f.write(content)
        return main_path

    def _generate_platformio_ini(self, canvas: CanvasGraph, firmware_dir: str) -> str:
        """Generate platformio.ini for ESP32."""
        content = """; Parakram AI — Auto-generated PlatformIO config
[env:esp32]
platform = espressif32
board = esp32dev
framework = arduino
monitor_speed = 115200
lib_deps =
"""
        ini_path = os.path.join(firmware_dir, "platformio.ini")
        with open(ini_path, "w") as f:
            f.write(content)
        return ini_path
