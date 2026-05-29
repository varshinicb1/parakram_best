"""
FreeRTOS-Aware Code Assembler

When FreeRTOS blocks are present in the system graph, generates
xTaskCreatePinnedToCore-based firmware instead of millis() polling.
Each block category gets its own task pinned to a core, with queues
bridging data between tasks and semaphores protecting shared buses.
"""

import os
from models.system_models import SystemGraph, HardwareAllocation, AssembledFirmware, TaskSchedule


# Core assignments by category
CORE_ASSIGNMENTS = {
    "sensor": 0,       # Core 0: data acquisition
    "audio": 0,        # Core 0: I2S DMA
    "communication": 1, # Core 1: WiFi/BLE/MQTT
    "display": 1,      # Core 1: LVGL rendering
    "actuator": 1,     # Core 1: output control
    "logic": 1,        # Core 1: control logic
    "control": 1,      # Core 1: control blocks
    "security": 1,     # Core 1: crypto
    "freertos": -1,    # No default — configured per block
}

# Default stack sizes by category (bytes)
STACK_SIZES = {
    "sensor": 4096,
    "audio": 8192,       # FFT/DMA needs more stack
    "communication": 8192, # TLS/WiFi are stack-hungry
    "display": 16384,     # LVGL needs lots of stack
    "actuator": 2048,
    "logic": 2048,
    "control": 2048,
    "security": 4096,
    "freertos": 4096,
}

# Priorities (higher = more important)
PRIORITIES = {
    "audio": 10,        # Real-time audio
    "sensor": 8,        # Fast data acquisition
    "control": 6,       # Control logic
    "logic": 6,
    "actuator": 5,
    "display": 4,       # UI can lag slightly
    "communication": 3, # Network is tolerant
    "security": 3,
    "freertos": 5,
}


class FreeRTOSAssembler:
    """
    Generates FreeRTOS task-based main.cpp when RTOS blocks are detected.
    Falls back gracefully if no FreeRTOS blocks are present.
    """

    def has_freertos_blocks(self, system_graph: SystemGraph) -> bool:
        """Check if the graph contains any FreeRTOS blocks."""
        for node in system_graph.original_nodes:
            if node.get("category") == "freertos":
                return True
        return False

    def assemble(
        self,
        project_id: str,
        system_graph: SystemGraph,
        allocation: HardwareAllocation,
        project_dir: str,
    ) -> AssembledFirmware:
        """Generate FreeRTOS-based firmware files."""

        # Gather all nodes
        all_nodes = list(system_graph.original_nodes)
        for n in system_graph.inferred_nodes:
            all_nodes.append({
                "id": n.id,
                "name": n.name,
                "category": n.category or "control",
                "configuration": n.configuration,
                "inputs": n.inputs,
                "outputs": n.outputs,
            })

        # Group by category for task assignment
        categories: dict[str, list[dict]] = {}
        for node in all_nodes:
            cat = node.get("category", "logic")
            if cat not in categories:
                categories[cat] = []
            categories[cat].append(node)

        # Detect shared buses that need semaphores
        i2c_nodes = [n for n in all_nodes if self._uses_i2c(n)]
        spi_nodes = [n for n in all_nodes if self._uses_spi(n)]
        needs_i2c_mutex = len(i2c_nodes) > 1
        needs_spi_mutex = len(spi_nodes) > 1

        # Generate files
        os.makedirs(os.path.join(project_dir, "firmware", "src"), exist_ok=True)
        os.makedirs(os.path.join(project_dir, "firmware", "include"), exist_ok=True)

        main_cpp = self._generate_main_cpp(categories, needs_i2c_mutex, needs_spi_mutex, allocation)
        globals_h = self._generate_globals_h(all_nodes, allocation, needs_i2c_mutex, needs_spi_mutex)
        config_h = self._generate_config_h(all_nodes, allocation)

        files = []
        file_pairs = [
            (os.path.join(project_dir, "firmware", "include", "globals.h"), globals_h),
            (os.path.join(project_dir, "firmware", "include", "config.h"), config_h),
            (os.path.join(project_dir, "firmware", "src", "main.cpp"), main_cpp),
        ]

        for path, content in file_pairs:
            with open(path, "w", encoding="utf-8") as f:
                f.write(content)
            files.append(path)

        # Build schedule info
        schedule = []
        for cat, nodes in categories.items():
            for node in nodes:
                node_id = node.get("id", "")
                name = node.get("name", node_id)
                safe_name = self._safe_name(name)
                config = node.get("configuration", {})
                interval = int(config.get("read_interval", config.get("interval_ms", 1000)))

                schedule.append(TaskSchedule(
                    node_id=node_id,
                    function_name=f"{safe_name}_loop",
                    interval_ms=interval,
                    priority=PRIORITIES.get(cat, 5),
                    category=cat,
                ))

        return AssembledFirmware(
            files=files,
            init_order=[n.get("id", "") for n in all_nodes],
            schedule=schedule,
            library_deps=self._collect_library_deps(all_nodes),
        )

    def _generate_main_cpp(
        self,
        categories: dict[str, list[dict]],
        needs_i2c_mutex: bool,
        needs_spi_mutex: bool,
        allocation: HardwareAllocation,
    ) -> str:
        lines = [
            "// ============================================",
            "// Parakram AI -- FreeRTOS Firmware",
            "// Auto-generated -- do not edit manually",
            "// ============================================",
            "",
            "#include <Arduino.h>",
            "#include <freertos/FreeRTOS.h>",
            "#include <freertos/task.h>",
            "#include <freertos/queue.h>",
            "#include <freertos/semphr.h>",
            "#include <freertos/event_groups.h>",
            '#include "globals.h"',
            '#include "config.h"',
            "",
        ]

        # Semaphore declarations
        if needs_i2c_mutex:
            lines.append("SemaphoreHandle_t i2c_mutex = NULL;")
        if needs_spi_mutex:
            lines.append("SemaphoreHandle_t spi_mutex = NULL;")
        lines.append("EventGroupHandle_t system_events = NULL;")
        lines.append("")

        # Event bits
        lines.append("// System event bits")
        lines.append("#define EVT_WIFI_READY   (1 << 0)")
        lines.append("#define EVT_SENSORS_OK   (1 << 1)")
        lines.append("#define EVT_MQTT_CONN    (1 << 2)")
        lines.append("#define EVT_SYSTEM_READY (1 << 3)")
        lines.append("")

        # Forward declarations for task functions
        lines.append("// --- Task functions ---")
        for cat, nodes in categories.items():
            task_name = f"task_{cat}"
            lines.append(f"void {task_name}(void* params);")
        lines.append("")

        # Forward declarations for block functions
        lines.append("// --- Block functions ---")
        for cat, nodes in categories.items():
            for node in nodes:
                name = self._safe_name(node.get("name", node.get("id", "")))
                lines.append(f"void {name}_setup();")
                lines.append(f"void {name}_loop();")
        lines.append("")

        # setup()
        lines.append("void setup() {")
        lines.append("    Serial.begin(115200);")
        lines.append('    Serial.println("[system] Parakram AI FreeRTOS starting...");')
        lines.append("")

        if needs_i2c_mutex:
            lines.append("    // Create I2C bus mutex")
            lines.append("    i2c_mutex = xSemaphoreCreateMutex();")
        if needs_spi_mutex:
            lines.append("    // Create SPI bus mutex")
            lines.append("    spi_mutex = xSemaphoreCreateMutex();")
        lines.append("    system_events = xEventGroupCreate();")
        lines.append("")

        # Initialize blocks
        lines.append("    // Initialize all blocks")
        for cat, nodes in categories.items():
            for node in nodes:
                name = self._safe_name(node.get("name", node.get("id", "")))
                lines.append(f"    {name}_setup();")
        lines.append("")

        # Create tasks per category
        lines.append("    // Create FreeRTOS tasks per category")
        for cat, nodes in categories.items():
            if cat == "freertos":
                continue  # FreeRTOS blocks are infrastructure, not tasks
            core = CORE_ASSIGNMENTS.get(cat, 1)
            stack = STACK_SIZES.get(cat, 4096)
            priority = PRIORITIES.get(cat, 5)
            task_name = f"task_{cat}"
            lines.append(f'    xTaskCreatePinnedToCore({task_name}, "{cat}", {stack}, NULL, {priority}, NULL, {core});')
        lines.append("")
        lines.append('    Serial.println("[system] All tasks created");')
        lines.append("    xEventGroupSetBits(system_events, EVT_SYSTEM_READY);")
        lines.append("}")
        lines.append("")

        # loop() — minimal in FreeRTOS mode
        lines.append("void loop() {")
        lines.append("    // FreeRTOS handles scheduling — loop() can yield")
        lines.append("    vTaskDelay(pdMS_TO_TICKS(1000));")
        lines.append("}")
        lines.append("")

        # Task implementations
        for cat, nodes in categories.items():
            if cat == "freertos":
                continue
            task_name = f"task_{cat}"
            config = nodes[0].get("configuration", {}) if nodes else {}
            interval = int(config.get("read_interval", config.get("interval_ms", 1000)))

            lines.append(f"void {task_name}(void* params) {{")
            lines.append(f'    Serial.printf("[{cat}] Task started on core %d\\n", xPortGetCoreID());')
            lines.append("    for (;;) {")

            for node in nodes:
                name = self._safe_name(node.get("name", node.get("id", "")))
                uses_i2c = self._uses_i2c(node)
                uses_spi = self._uses_spi(node)

                if uses_i2c and needs_i2c_mutex:
                    lines.append("        if (xSemaphoreTake(i2c_mutex, pdMS_TO_TICKS(100)) == pdTRUE) {")
                    lines.append(f"            {name}_loop();")
                    lines.append("            xSemaphoreGive(i2c_mutex);")
                    lines.append("        }")
                elif uses_spi and needs_spi_mutex:
                    lines.append("        if (xSemaphoreTake(spi_mutex, pdMS_TO_TICKS(100)) == pdTRUE) {")
                    lines.append(f"            {name}_loop();")
                    lines.append("            xSemaphoreGive(spi_mutex);")
                    lines.append("        }")
                else:
                    lines.append(f"        {name}_loop();")

            lines.append(f"        vTaskDelay(pdMS_TO_TICKS({interval}));")
            lines.append("    }")
            lines.append("}")
            lines.append("")

        return "\n".join(lines)

    def _generate_globals_h(
        self, nodes: list[dict], allocation: HardwareAllocation,
        needs_i2c_mutex: bool, needs_spi_mutex: bool
    ) -> str:
        lines = [
            "#ifndef GLOBALS_H",
            "#define GLOBALS_H",
            "",
            "#include <Arduino.h>",
            "#include <freertos/FreeRTOS.h>",
            "#include <freertos/semphr.h>",
            "#include <freertos/event_groups.h>",
            "",
            "// --- Bus mutexes ---",
        ]
        if needs_i2c_mutex:
            lines.append("extern SemaphoreHandle_t i2c_mutex;")
        if needs_spi_mutex:
            lines.append("extern SemaphoreHandle_t spi_mutex;")
        lines.append("extern EventGroupHandle_t system_events;")
        lines.append("")

        # Pin definitions
        lines.append("// --- Pin Definitions ---")
        for pin in allocation.pins:
            pin_name = f"PIN_{pin.node_id.upper()}_{pin.function.upper()}"
            pin_name = pin_name.replace(" ", "_").replace("-", "_")
            lines.append(f"#define {pin_name} {pin.pin}")
        lines.append("")

        # Shared state
        lines.append("// --- Shared State (volatile for multi-task access) ---")
        for node in nodes:
            outputs = node.get("outputs", [])
            node_name = self._safe_name(node.get("name", node.get("id", "")))
            for out in outputs:
                var_type = self._cpp_type(out.get("data_type", "float"))
                var_name = f"{node_name}_{out.get('name', 'value')}"
                lines.append(f"extern volatile {var_type} {var_name};")
        lines.append("")
        lines.append("#endif")
        return "\n".join(lines)

    def _generate_config_h(self, nodes: list[dict], allocation: HardwareAllocation) -> str:
        lines = [
            "#ifndef CONFIG_H",
            "#define CONFIG_H",
            "",
            "// --- Compile-time config ---",
        ]
        for node in nodes:
            config = node.get("configuration", {})
            node_name = self._safe_name(node.get("name", node.get("id", ""))).upper()
            for key, val in config.items():
                lines.append(f"#define CFG_{node_name}_{key.upper()} {val}")
        lines.append("")

        # Memory budget
        lines.append("// --- Memory Budget ---")
        lines.append(f"#define FLASH_BUDGET {allocation.memory.flash_bytes}")
        lines.append(f"#define SRAM_BUDGET {allocation.memory.sram_bytes}")
        lines.append("")
        lines.append("#endif")
        return "\n".join(lines)

    # ─── Helpers ─────────────────────────────────────────────

    def _safe_name(self, name: str) -> str:
        return name.lower().replace(" ", "_").replace("-", "_").replace(".", "_")

    def _uses_i2c(self, node: dict) -> bool:
        config = node.get("configuration", {})
        return "i2c_address" in config or "sda_pin" in config

    def _uses_spi(self, node: dict) -> bool:
        config = node.get("configuration", {})
        name = node.get("name", "").lower()
        return "cs_pin" in config or "spi_freq" in config or "tft" in name or "spi" in name

    def _cpp_type(self, dt: str) -> str:
        return {"float": "float", "int": "int", "bool": "bool", "string": "String"}.get(dt, "float")

    def _collect_library_deps(self, nodes: list[dict]) -> list[str]:
        deps = set()
        for node in nodes:
            for lib in node.get("libraries", []):
                deps.add(lib)
        return sorted(deps)
