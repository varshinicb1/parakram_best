"""
Code Assembly Engine — combines block modules into a runtime system.

Responsibilities:
  - Determine initialization order (topological sort with priority)
  - Generate millis()-based scheduler loop (replacing flat delay loops)
  - Produce globals.h and config.h for shared state
  - Collect library dependencies for platformio.ini

Pipeline step: SystemGraph + HardwareAllocation + firmware files → AssembledFirmware
"""

import os
import json
from models.system_models import (
    SystemGraph,
    HardwareAllocation,
    AssembledFirmware,
    TaskSchedule,
)


# Default execution intervals by category (milliseconds)
CATEGORY_INTERVALS = {
    "sensor": 2000,       # Sensors read every 2s
    "logic": 100,         # Logic checks every 100ms
    "actuator": 200,      # Actuators update every 200ms
    "communication": 5000, # Comms send every 5s
    "output": 1000,       # Output (serial) every 1s
}

CATEGORY_PRIORITIES = {
    "communication": 0,  # Init first (WiFi, MQTT need time)
    "sensor": 1,
    "logic": 2,
    "actuator": 3,
    "output": 4,
}


class CodeAssembler:
    """
    Assembles the final firmware from individual block modules.

    Produces:
    - main.cpp with millis()-based scheduling loop
    - globals.h with pin definitions and shared state
    - config.h with compile-time constants
    - platformio.ini with all library dependencies
    """

    def __init__(self):
        self.hardware_lib_dir = os.path.join(
            os.path.dirname(__file__),
            "..", "hardware_library"
        )

    def assemble(
        self,
        project_id: str,
        system_graph: SystemGraph,
        allocation: HardwareAllocation,
        project_dir: str,
    ) -> AssembledFirmware:
        """
        Main entry point. Assemble the complete firmware.
        """
        firmware_dir = os.path.join(project_dir, "firmware")
        src_dir = os.path.join(firmware_dir, "src")
        include_dir = os.path.join(firmware_dir, "include")
        os.makedirs(src_dir, exist_ok=True)
        os.makedirs(include_dir, exist_ok=True)

        # Collect all nodes
        all_nodes = list(system_graph.original_nodes)
        for inf in system_graph.inferred_nodes:
            all_nodes.append(inf.model_dump())

        # Determine initialization order
        init_order = self._determine_init_order(system_graph)

        # Build task schedule
        schedule = self._build_schedule(all_nodes)

        # Collect library dependencies
        lib_deps = self._collect_library_deps(all_nodes)

        # Generate output files
        globals_h = self._generate_globals_h(allocation, all_nodes)
        config_h = self._generate_config_h(system_graph, allocation, all_nodes)
        main_cpp = self._generate_main_cpp(init_order, schedule, all_nodes, allocation)
        platformio_ini = self._generate_platformio_ini(lib_deps, allocation.board)

        # Write files
        files = []

        globals_path = os.path.join(include_dir, "globals.h")
        with open(globals_path, "w", encoding="utf-8") as f:
            f.write(globals_h)
        files.append(globals_path)

        config_path = os.path.join(include_dir, "config.h")
        with open(config_path, "w", encoding="utf-8") as f:
            f.write(config_h)
        files.append(config_path)

        main_path = os.path.join(src_dir, "main.cpp")
        with open(main_path, "w", encoding="utf-8") as f:
            f.write(main_cpp)
        files.append(main_path)

        ini_path = os.path.join(firmware_dir, "platformio.ini")
        with open(ini_path, "w", encoding="utf-8") as f:
            f.write(platformio_ini)
        files.append(ini_path)

        return AssembledFirmware(
            project_id=project_id,
            files=files,
            main_cpp=main_cpp,
            globals_h=globals_h,
            config_h=config_h,
            platformio_ini=platformio_ini,
            schedule=schedule,
            init_order=init_order,
            library_deps=lib_deps,
            allocation=allocation,
            system_graph=system_graph,
        )

    # ─── Initialization Order ────────────────────────────────

    def _determine_init_order(self, system_graph: SystemGraph) -> list[str]:
        """
        Determine setup() call order.
        Communication blocks first (WiFi needs time), then sensors,
        then logic, then actuators.
        Uses execution_order from the planner but re-sorts by priority.
        """
        all_nodes = {}
        for node in system_graph.original_nodes:
            all_nodes[node["id"]] = node
        for inf in system_graph.inferred_nodes:
            all_nodes[inf.id] = inf.model_dump()

        # Sort by category priority, preserving topological order within each
        def sort_key(node_id: str) -> tuple[int, int]:
            node = all_nodes.get(node_id, {})
            category = node.get("category", "logic")
            priority = CATEGORY_PRIORITIES.get(category, 99)
            topo_idx = (
                system_graph.execution_order.index(node_id)
                if node_id in system_graph.execution_order
                else 999
            )
            return (priority, topo_idx)

        return sorted(all_nodes.keys(), key=sort_key)

    # ─── Task Scheduling ─────────────────────────────────────

    def _build_schedule(self, all_nodes: list[dict]) -> list[TaskSchedule]:
        """
        Create timing-aware task schedule.
        Each block runs at a category-appropriate interval.
        """
        schedule = []
        for node in all_nodes:
            node_id = node.get("id", "unknown")
            node_name = node.get("name", node_id)
            category = node.get("category", "logic")
            config = node.get("configuration", {})

            safe_name = node_name.lower().replace(" ", "_").replace("-", "_")
            safe_name = "".join(c for c in safe_name if c.isalnum() or c == "_")

            # User-specified interval overrides default
            interval = config.get("read_interval") or config.get("interval")
            if interval:
                interval = int(interval)
            else:
                interval = CATEGORY_INTERVALS.get(category, 1000)

            schedule.append(TaskSchedule(
                node_id=node_id,
                function_name=f"{safe_name}_loop",
                interval_ms=interval,
                priority=CATEGORY_PRIORITIES.get(category, 99),
                category=category,
            ))

        # Sort by priority
        schedule.sort(key=lambda t: t.priority)
        return schedule

    # ─── Main.cpp Generation ─────────────────────────────────

    def _generate_main_cpp(
        self,
        init_order: list[str],
        schedule: list[TaskSchedule],
        all_nodes: list[dict],
        allocation: HardwareAllocation,
    ) -> str:
        """
        Generate main.cpp with millis()-based scheduling loop.
        """
        node_map = {n.get("id", ""): n for n in all_nodes}

        # Build includes
        includes = ['#include <Arduino.h>', '#include "globals.h"', '#include "config.h"']
        for node_id in init_order:
            node = node_map.get(node_id, {})
            name = node.get("name", node_id)
            safe = self._safe_name(name)
            includes.append(f'#include "{safe}.h"')

        # Build setup calls
        setup_lines = []
        for node_id in init_order:
            node = node_map.get(node_id, {})
            name = node.get("name", node_id)
            safe = self._safe_name(name)
            setup_lines.append(f'    Serial.println("[init] {name}...");')
            setup_lines.append(f"    {safe}_setup();")

        # Build scheduler variables
        timer_vars = []
        loop_blocks = []

        for task in schedule:
            var_name = f"last_{task.function_name}"
            timer_vars.append(f"unsigned long {var_name} = 0;")

            loop_blocks.append(f"""\
    // {task.category.upper()}: {task.function_name} — every {task.interval_ms}ms
    if (now - {var_name} >= {task.interval_ms}) {{
        {var_name} = now;
        {task.function_name}();
    }}""")

        # Interrupt handlers
        isr_lines = []
        for intr in allocation.interrupts:
            isr_lines.append(f"""
volatile bool {intr.handler}_flag = false;
void IRAM_ATTR {intr.handler}() {{
    {intr.handler}_flag = true;
}}""")

        # Interrupt attachments in setup
        isr_setup = []
        for intr in allocation.interrupts:
            isr_setup.append(
                f"    attachInterrupt(digitalPinToInterrupt({intr.pin}), "
                f"{intr.handler}, {intr.trigger});"
            )

        # ─── Assemble main.cpp ─────────────────

        content = f"""\
// ===========================================================
// Parakram AI -- Auto-Generated Firmware
// Board: {allocation.board}
// Nodes: {len(all_nodes)} ({len(schedule)} scheduled tasks)
// Generated by Code Assembly Engine
// ===========================================================

{chr(10).join(includes)}

// --- Scheduler Timers ---
{chr(10).join(timer_vars)}
"""

        if isr_lines:
            content += f"""
// --- Interrupt Service Routines ---
{chr(10).join(isr_lines)}
"""

        content += f"""
// --- Setup ---
void setup() {{
    Serial.begin(115200);
    delay(1000);
    Serial.println("====================================");
    Serial.println("  Parakram AI Firmware v0.1.0");
    Serial.println("  Board: {allocation.board}");
    Serial.println("  Tasks: {len(schedule)}");
    Serial.println("====================================");
    Serial.println();
    Serial.println("[boot] Initializing modules...");

{chr(10).join(setup_lines)}
"""

        if isr_setup:
            content += f"""
    // Attach interrupt handlers
{chr(10).join(isr_setup)}
"""

        content += f"""
    Serial.println();
    Serial.println("[boot] All {len(all_nodes)} modules initialized.");
    Serial.println("[boot] Scheduler starting...");
    Serial.println();
}}

// --- Scheduling Loop ---
void loop() {{
    unsigned long now = millis();

{chr(10).join(loop_blocks)}
}}
"""
        return content

    # ─── Globals Header ──────────────────────────────────────

    def _generate_globals_h(
        self, allocation: HardwareAllocation, all_nodes: list[dict]
    ) -> str:
        """
        Generate globals.h with pin definitions and shared state declarations.
        """
        lines = [
            "#ifndef GLOBALS_H",
            "#define GLOBALS_H",
            "",
            "#include <Arduino.h>",
            "",
            "// === Pin Definitions ===========================",
        ]

        for pin_alloc in allocation.pins:
            define_name = f"PIN_{pin_alloc.function.upper()}"
            lines.append(f"#define {define_name} {pin_alloc.pin}")

        lines.append("")
        lines.append("// === I2C Bus Configuration ========================")
        for bus in allocation.buses:
            if bus.devices:
                lines.append(f"// Bus {bus.bus_id}: SDA={bus.sda_pin}, SCL={bus.scl_pin}")
                for dev in bus.devices:
                    lines.append(f"//   Device: {dev.get('name', '?')} @ {dev.get('address', '?')}")

        lines.append("")
        lines.append("// === Shared State Variables =======================")
        for node in all_nodes:
            safe = self._safe_name(node.get("name", ""))
            outputs = node.get("outputs", [])
            for out in outputs:
                out_name = out.get("name", "value") if isinstance(out, dict) else out.name
                out_type = out.get("data_type", "float") if isinstance(out, dict) else out.data_type
                cpp_type = self._to_cpp_type(out_type)
                lines.append(f"extern {cpp_type} {safe}_{out_name};")

        lines.extend(["", "#endif // GLOBALS_H", ""])
        return "\n".join(lines)

    # ─── Config Header ───────────────────────────────────────

    def _generate_config_h(
        self,
        system_graph: SystemGraph,
        allocation: HardwareAllocation,
        all_nodes: list[dict],
    ) -> str:
        """
        Generate config.h with compile-time constants from block configuration.
        """
        lines = [
            "#ifndef CONFIG_H",
            "#define CONFIG_H",
            "",
            "// === Block Configuration Constants ===================",
            f"// Total blocks: {len(all_nodes)}",
            f"// Board: {allocation.board}",
            "",
        ]

        for node in all_nodes:
            safe = self._safe_name(node.get("name", ""))
            config = node.get("configuration", {})
            node_name = node.get("name", "Unknown")

            if not config:
                continue

            lines.append(f"// --- {node_name} ---")
            for key, value in config.items():
                define_name = f"CFG_{safe.upper()}_{key.upper()}"
                if isinstance(value, bool):
                    lines.append(f"#define {define_name} {'true' : 'false'}")
                elif isinstance(value, (int, float)):
                    lines.append(f"#define {define_name} {value}")
                elif isinstance(value, str):
                    # Strings with quotes for SSID/password, raw for others
                    if key in ("ssid", "password", "broker", "topic", "format"):
                        lines.append(f'#define {define_name} "{value}"')
                    else:
                        lines.append(f"#define {define_name} {value}")
            lines.append("")

        # Memory budget constants
        mem = allocation.memory
        lines.extend([
            "// === Memory Budget =================================",
            f"// Flash: {mem.flash_bytes:,} bytes ({mem.flash_percent:.1f}%)",
            f"// SRAM:  {mem.sram_bytes:,} bytes ({mem.sram_percent:.1f}%)",
            "",
            "#endif // CONFIG_H",
            "",
        ])

        return "\n".join(lines)

    # ─── PlatformIO Config ───────────────────────────────────

    def _generate_platformio_ini(
        self, lib_deps: list[str], board: str
    ) -> str:
        """Generate platformio.ini with all collected library dependencies."""
        deps_lines = "\n".join(f"    {dep}" for dep in lib_deps) if lib_deps else "    ; No external libraries"

        return f"""; ===========================================================
; Parakram AI -- Auto-Generated PlatformIO Configuration
; ===========================================================""" + f"""

[env:{board}]
platform = espressif32
board = {board}
framework = arduino
monitor_speed = 115200

; Build flags
build_flags =
    -DCORE_DEBUG_LEVEL=1
    -DBOARD_HAS_PSRAM=0

; Library dependencies (auto-collected from block definitions)
lib_deps =
{deps_lines}

; Upload settings
upload_speed = 921600

; Monitor settings
monitor_filters = esp32_exception_decoder
"""

    # ─── Library Dependencies ────────────────────────────────

    def _collect_library_deps(self, all_nodes: list[dict]) -> list[str]:
        """
        Collect PlatformIO library dependencies from all blocks.
        Reads from hardware library JSON definitions.
        """
        deps = set()

        for node in all_nodes:
            block_id = node.get("block_id", "")
            category = node.get("category", "")

            # Try to load the hardware library definition
            lib_def = self._load_block_library(block_id, category)
            if lib_def and "libraries" in lib_def:
                for lib in lib_def["libraries"]:
                    deps.add(lib)

            # Check for common auto-detected dependencies
            name_lower = node.get("name", "").lower()
            if "wifi" in name_lower:
                deps.add("knolleary/PubSubClient@^2.8")
            if "mqtt" in name_lower:
                deps.add("knolleary/PubSubClient@^2.8")
            if "servo" in name_lower:
                deps.add("madhephaestus/ESP32Servo@^1.1.1")

        return sorted(deps)

    def _load_block_library(self, block_id: str, category: str) -> dict | None:
        """Try to load a block's library definition JSON."""
        # Map category to subdirectory
        cat_dirs = {
            "sensor": "sensors",
            "actuator": "actuators",
            "communication": "communication",
        }
        subdir = cat_dirs.get(category, "")
        if not subdir:
            return None

        # Try to find the JSON file
        search_dir = os.path.join(self.hardware_lib_dir, subdir)
        if not os.path.isdir(search_dir):
            return None

        for filename in os.listdir(search_dir):
            if filename.endswith(".json"):
                filepath = os.path.join(search_dir, filename)
                try:
                    with open(filepath) as f:
                        data = json.load(f)
                    if data.get("id") == block_id:
                        return data
                except (json.JSONDecodeError, IOError):
                    continue

        return None

    # ─── Helpers ─────────────────────────────────────────────

    def _safe_name(self, name: str) -> str:
        """Convert a block name to a C-safe identifier."""
        safe = name.lower().replace(" ", "_").replace("-", "_")
        return "".join(c for c in safe if c.isalnum() or c == "_")

    def _to_cpp_type(self, data_type: str) -> str:
        """Convert a Parakram data type to a C++ type."""
        type_map = {
            "float": "float",
            "int": "int",
            "bool": "bool",
            "digital": "bool",
            "analog": "int",
            "string": "String",
            "any": "String",
        }
        return type_map.get(data_type, "String")
