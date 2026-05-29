"""
Hardware Resource Manager — allocates hardware resources automatically.

Responsibilities:
  - GPIO pin allocation (respecting board constraints)
  - I2C bus sharing (address conflict detection)
  - Interrupt allocation (for blocks that need ISRs)
  - Memory estimation (Flash + SRAM usage)

Pipeline step: SystemGraph → HardwareAllocation
"""

import os
import json
from models.system_models import (
    SystemGraph,
    HardwareAllocation,
    PinAllocation,
    BusAllocation,
    InterruptAllocation,
    MemoryEstimate,
)


class ResourceManager:
    """
    Allocates hardware resources for an embedded system graph.
    Uses board manifests to enforce constraints (pin capabilities,
    bus limits, memory budget).
    """

    def __init__(self):
        self.boards_dir = os.path.join(
            os.path.dirname(__file__),
            "..", "hardware_library", "boards"
        )

    def allocate(
        self, system_graph: SystemGraph, board: str = "esp32dev"
    ) -> HardwareAllocation:
        """
        Main entry point. Allocate all hardware resources.
        """
        manifest = self._load_board_manifest(board)
        all_nodes = self._collect_all_nodes(system_graph)

        # Allocate in order: GPIO → I2C → interrupts → memory
        pins, used_pins, pin_conflicts, pin_warnings = self._allocate_gpio(
            all_nodes, manifest
        )
        buses, bus_warnings = self._allocate_i2c(all_nodes, manifest, used_pins)
        interrupts, int_warnings = self._allocate_interrupts(
            all_nodes, manifest, used_pins
        )
        memory = self._estimate_memory(all_nodes, manifest)

        # Compute remaining available pins
        all_usable = set(manifest["gpio"]["safe_pins"] + manifest["gpio"]["input_only_pins"])
        available = sorted(all_usable - used_pins)

        all_warnings = pin_warnings + bus_warnings + int_warnings

        # Memory budget warning
        if memory.sram_percent > 80:
            all_warnings.append(
                f"⚠ SRAM usage is {memory.sram_percent:.1f}% — may be unstable"
            )
        if memory.flash_percent > 90:
            all_warnings.append(
                f"⚠ Flash usage is {memory.flash_percent:.1f}% — near limit"
            )

        return HardwareAllocation(
            board=board,
            pins=pins,
            buses=buses,
            interrupts=interrupts,
            memory=memory,
            pin_conflicts=pin_conflicts,
            warnings=all_warnings,
            available_pins=available,
        )

    # ─── Board Manifest ──────────────────────────────────────

    def _load_board_manifest(self, board: str) -> dict:
        """Load the board's hardware manifest JSON."""
        manifest_path = os.path.join(self.boards_dir, f"{board}_manifest.json")
        if not os.path.exists(manifest_path):
            # Try without "dev" suffix
            alt_path = os.path.join(self.boards_dir, "esp32_manifest.json")
            if os.path.exists(alt_path):
                manifest_path = alt_path
            else:
                raise FileNotFoundError(
                    f"Board manifest not found: {board}. "
                    f"Expected at {manifest_path}"
                )
        with open(manifest_path) as f:
            return json.load(f)

    def _collect_all_nodes(self, system_graph: SystemGraph) -> list[dict]:
        """Combine original and inferred nodes into a flat list."""
        nodes = list(system_graph.original_nodes)
        for inferred in system_graph.inferred_nodes:
            nodes.append(inferred.model_dump())
        return nodes

    # ─── GPIO Allocation ─────────────────────────────────────

    def _allocate_gpio(
        self, nodes: list[dict], manifest: dict
    ) -> tuple[list[PinAllocation], set[int], list[str], list[str]]:
        """
        Allocate GPIO pins for all blocks.

        Strategy:
        1. Respect user-configured pin values (from block configuration)
        2. Auto-assign from safe_pins pool for blocks without explicit pins
        3. Use input_only_pins for sensor-only blocks when safe_pins run out
        4. Detect and report conflicts
        """
        safe_pins = list(manifest["gpio"]["safe_pins"])
        input_only = list(manifest["gpio"]["input_only_pins"])
        reserved = set(int(k) for k in manifest["gpio"].get("reserved_pins", {}).keys())

        allocations = []
        used_pins: set[int] = set()
        conflicts = []
        warnings = []

        # Pool of pins available for auto-assignment
        auto_pool = [p for p in safe_pins if p not in reserved]
        input_pool = [p for p in input_only if p not in reserved]

        for node in nodes:
            config = node.get("configuration", {})
            category = node.get("category", "logic")
            node_id = node.get("id", "unknown")
            node_name = node.get("name", node_id)

            # Check if user specified a pin
            user_pin = config.get("pin")
            if user_pin is not None:
                pin = int(user_pin)
                if pin in used_pins:
                    conflicts.append(
                        f"Pin {pin} conflict: already allocated, "
                        f"requested by '{node_name}'"
                    )
                elif pin in reserved:
                    warnings.append(
                        f"Pin {pin} is reserved ({manifest['gpio']['reserved_pins'].get(str(pin), 'system')}), "
                        f"used by '{node_name}'"
                    )

                direction = "input" if category == "sensor" else "output"
                mode = "digital"

                # Detect analog/PWM needs
                if config.get("mode") == "analog" or "analog" in str(config.get("type", "")):
                    mode = "analog"
                elif category == "actuator" and "servo" in node_name.lower():
                    mode = "pwm"

                allocations.append(PinAllocation(
                    pin=pin,
                    node_id=node_id,
                    function=f"{node_name.lower().replace(' ', '_')}",
                    mode=mode,
                    direction=direction,
                ))
                used_pins.add(pin)
            else:
                # Auto-assign: sensors can use input_only pins
                if category == "sensor":
                    pool = auto_pool if auto_pool else input_pool
                elif category in ("actuator", "output"):
                    pool = auto_pool
                else:
                    # Logic and inferred nodes don't need GPIO
                    continue

                if not pool:
                    warnings.append(
                        f"No GPIO pins available for '{node_name}' — "
                        f"all pins allocated"
                    )
                    continue

                pin = pool.pop(0)
                used_pins.add(pin)

                direction = "input" if category == "sensor" else "output"
                mode = "pwm" if "servo" in node_name.lower() else "digital"

                allocations.append(PinAllocation(
                    pin=pin,
                    node_id=node_id,
                    function=f"{node_name.lower().replace(' ', '_')}_auto",
                    mode=mode,
                    direction=direction,
                ))
                warnings.append(
                    f"Auto-assigned GPIO {pin} to '{node_name}'"
                )

                # Remove from the other pool too
                if pin in auto_pool:
                    auto_pool.remove(pin)
                if pin in input_pool:
                    input_pool.remove(pin)

        return allocations, used_pins, conflicts, warnings

    # ─── I2C Bus Allocation ──────────────────────────────────

    def _allocate_i2c(
        self, nodes: list[dict], manifest: dict, used_pins: set[int]
    ) -> tuple[list[BusAllocation], list[str]]:
        """
        Allocate I2C devices to available buses.
        Detect address conflicts within the same bus.
        """
        warnings = []
        i2c_devices = []

        # Find nodes that use I2C
        for node in nodes:
            config = node.get("configuration", {})
            if "i2c_address" in config or "i2c" in str(config.get("interface", "")):
                i2c_devices.append({
                    "node_id": node.get("id"),
                    "name": node.get("name"),
                    "address": config.get("i2c_address", "0x00"),
                })

        if not i2c_devices:
            return [], warnings

        # Assign to available buses
        available_buses = manifest.get("i2c", [])
        if not available_buses:
            warnings.append("No I2C buses available on this board")
            return [], warnings

        allocations = []
        for bus_def in available_buses:
            bus_alloc = BusAllocation(
                bus_id=bus_def["bus_id"],
                bus_type="i2c",
                sda_pin=bus_def["default_sda"],
                scl_pin=bus_def["default_scl"],
                devices=[],
            )
            allocations.append(bus_alloc)

        # Distribute devices across buses (round-robin for now)
        used_addresses: dict[int, set] = {b.bus_id: set() for b in allocations}

        for i, device in enumerate(i2c_devices):
            bus_idx = i % len(allocations)
            bus = allocations[bus_idx]
            addr = device["address"]

            if addr in used_addresses[bus.bus_id]:
                warnings.append(
                    f"I2C address conflict: {addr} on bus {bus.bus_id}, "
                    f"device '{device['name']}'"
                )
            else:
                used_addresses[bus.bus_id].add(addr)

            bus.devices.append({
                "node_id": device["node_id"],
                "address": addr,
                "name": device["name"],
            })

        # Mark I2C pins as used
        for bus in allocations:
            if bus.devices:  # Only if bus is actually used
                used_pins.add(bus.sda_pin)
                used_pins.add(bus.scl_pin)

        return allocations, warnings

    # ─── Interrupt Allocation ────────────────────────────────

    def _allocate_interrupts(
        self, nodes: list[dict], manifest: dict, used_pins: set[int]
    ) -> tuple[list[InterruptAllocation], list[str]]:
        """
        Allocate interrupt-capable pins for blocks that need ISRs.
        """
        warnings = []
        int_capable = set(manifest["gpio"].get("interrupt_capable_pins", []))
        available_int_pins = sorted(int_capable - used_pins)

        allocations = []

        for node in nodes:
            config = node.get("configuration", {})
            needs_interrupt = (
                config.get("interrupt", False)
                or config.get("trigger") in ("rising", "falling", "change")
                or node.get("inferred_type") == "debounce"
            )

            if not needs_interrupt:
                continue

            node_id = node.get("id", "unknown")
            node_name = node.get("name", node_id)

            if not available_int_pins:
                warnings.append(
                    f"No interrupt-capable pins available for '{node_name}'"
                )
                continue

            pin = available_int_pins.pop(0)
            used_pins.add(pin)

            trigger = config.get("trigger", "rising").upper()
            safe_name = node_name.lower().replace(" ", "_")

            allocations.append(InterruptAllocation(
                pin=pin,
                node_id=node_id,
                trigger=trigger,
                handler=f"isr_{safe_name}",
            ))

        return allocations, warnings

    # ─── Memory Estimation ───────────────────────────────────

    def _estimate_memory(
        self, nodes: list[dict], manifest: dict
    ) -> MemoryEstimate:
        """
        Estimate Flash and SRAM usage based on block types and libraries.
        """
        estimates = manifest.get("memory_estimates", {})
        total_flash = manifest["memory"]["flash_bytes"]
        total_sram = manifest["memory"]["sram_bytes"]

        flash = estimates.get("base_firmware_flash", 250000)
        sram = estimates.get("base_firmware_sram", 40000)
        breakdown = {}

        for node in nodes:
            category = node.get("category", "logic")
            node_id = node.get("id", "unknown")
            node_name = node.get("name", node_id)

            if category == "sensor":
                nf = estimates.get("per_sensor_flash", 8000)
                ns = estimates.get("per_sensor_sram", 2000)
            elif category == "actuator":
                nf = estimates.get("per_actuator_flash", 4000)
                ns = estimates.get("per_actuator_sram", 1000)
            elif category == "communication":
                nf = estimates.get("per_comms_module_flash", 20000)
                ns = estimates.get("per_comms_module_sram", 8000)
                # WiFi adds significant overhead
                if "wifi" in node_name.lower():
                    nf += estimates.get("wifi_flash", 180000)
                    ns += estimates.get("wifi_sram", 60000)
            else:
                nf = estimates.get("per_logic_block_flash", 2000)
                ns = estimates.get("per_logic_block_sram", 500)

            flash += nf
            sram += ns
            breakdown[node_id] = {"flash": nf, "sram": ns, "name": node_name}

        return MemoryEstimate(
            flash_bytes=flash,
            sram_bytes=sram,
            flash_percent=round(flash / total_flash * 100, 1),
            sram_percent=round(sram / total_sram * 100, 1),
            breakdown=breakdown,
        )
