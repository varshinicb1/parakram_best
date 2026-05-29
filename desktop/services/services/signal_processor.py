"""
Signal Processing Inserter -- automatically inserts preprocessing blocks.

Runs after the Logic Synthesizer, operating on SystemGraph.
Detects analog sensors, noisy signals, calibration needs, and
unit mismatches, inserting appropriate filter/conversion blocks.

Pipeline step: SystemGraph (synthesized) -> SystemGraph (processed)
"""

import uuid
from models.system_models import SystemGraph, SystemEdge, InferredNode


# ─── Auto-Insert Rules ───────────────────────────────────────

UNIT_CONVERSIONS = {
    ("celsius", "fahrenheit"): {"from_unit": "celsius", "to_unit": "fahrenheit"},
    ("fahrenheit", "celsius"): {"from_unit": "fahrenheit", "to_unit": "celsius"},
    ("meters", "feet"): {"from_unit": "meters", "to_unit": "feet"},
    ("feet", "meters"): {"from_unit": "feet", "to_unit": "meters"},
    ("pascals", "hectopascals"): {"from_unit": "pascals", "to_unit": "hectopascals"},
    ("hectopascals", "pascals"): {"from_unit": "hectopascals", "to_unit": "pascals"},
    ("radians", "degrees"): {"from_unit": "radians", "to_unit": "degrees"},
    ("degrees", "radians"): {"from_unit": "degrees", "to_unit": "radians"},
}


class SignalProcessor:
    """
    Automatically inserts signal preprocessing blocks into the system graph.

    Detects:
    1. Analog sensor outputs -> insert MovingAverage
    2. Sensor with calibration config -> insert Calibrator
    3. High-frequency sensor (< 500ms) -> insert LowPassFilter
    4. Source/target unit mismatch -> insert UnitConverter
    """

    def process(self, system_graph: SystemGraph) -> SystemGraph:
        """
        Main entry point. Analyze system graph and insert signal processing.
        """
        all_original = list(system_graph.original_nodes)
        all_inferred = list(system_graph.inferred_nodes)
        all_edges = list(system_graph.edges)
        warnings = list(system_graph.warnings)

        node_map = self._build_node_map(all_original, all_inferred)

        # Phase 1: Insert noise filters on analog sensor outputs
        new_n1, new_e1, rm_1, w1 = self._insert_noise_filters(
            all_original, all_edges, node_map
        )
        all_inferred.extend(new_n1)
        all_edges = [e for e in all_edges if e.id not in rm_1]
        all_edges.extend(new_e1)
        warnings.extend(w1)

        # Phase 2: Insert calibration blocks
        new_n2, new_e2, rm_2, w2 = self._insert_calibration(
            all_original, all_edges, node_map
        )
        all_inferred.extend(new_n2)
        all_edges = [e for e in all_edges if e.id not in rm_2]
        all_edges.extend(new_e2)
        warnings.extend(w2)

        # Phase 3: Insert low-pass filters on high-frequency sensors
        new_n3, new_e3, rm_3, w3 = self._insert_low_pass_filter(
            all_original, all_edges, node_map
        )
        all_inferred.extend(new_n3)
        all_edges = [e for e in all_edges if e.id not in rm_3]
        all_edges.extend(new_e3)
        warnings.extend(w3)

        # Phase 4: Insert unit converters
        new_n4, new_e4, rm_4, w4 = self._insert_unit_conversion(
            all_original, all_edges, node_map
        )
        all_inferred.extend(new_n4)
        all_edges = [e for e in all_edges if e.id not in rm_4]
        all_edges.extend(new_e4)
        warnings.extend(w4)

        # Rebuild execution order
        node_map = self._build_node_map(all_original, all_inferred)
        all_ids = list(node_map.keys())
        execution_order = self._topological_sort(all_ids, all_edges)

        return SystemGraph(
            original_nodes=all_original,
            inferred_nodes=all_inferred,
            edges=all_edges,
            execution_order=execution_order,
            warnings=warnings,
            data_type_errors=list(system_graph.data_type_errors),
        )

    # ─── Noise Filters (Moving Average) ──────────────────────

    def _insert_noise_filters(
        self,
        nodes: list[dict],
        edges: list[SystemEdge],
        node_map: dict,
    ) -> tuple[list[InferredNode], list[SystemEdge], set, list[str]]:
        """Insert MovingAverage on analog sensor outputs."""
        new_nodes = []
        new_edges = []
        remove_ids = set()
        warnings = []

        for node in nodes:
            if node.get("category") != "sensor":
                continue

            config = node.get("configuration", {})
            # Skip if user explicitly disabled filtering
            if config.get("no_filter", False):
                continue

            node_id = node.get("id", "")
            node_name = node.get("name", node_id)
            outputs = node.get("outputs", [])

            # Check for analog-type outputs
            for output in outputs:
                out_type = output.get("data_type", "")
                out_name = output.get("name", "value")

                if out_type not in ("float", "analog"):
                    continue

                # Find edges from this output
                outgoing = [
                    e for e in edges
                    if e.source == node_id and e.source_handle == out_name
                ]

                if not outgoing:
                    continue

                # Create MovingAverage node
                ma_id = f"signal_ma_{uuid.uuid4().hex[:8]}"
                window_size = 5  # Default

                ma_node = InferredNode(
                    id=ma_id,
                    name=f"Filter ({node_name}.{out_name})",
                    category="control",
                    inferred_type="moving_average",
                    description=f"Smooths noise on {node_name} {out_name}",
                    reason=f"Analog sensor output '{out_name}' benefits from noise filtering",
                    source_node_id=node_id,
                    target_node_id=outgoing[0].target,
                    configuration={"window_size": window_size},
                    inputs=[{"name": "value", "data_type": "float"}],
                    outputs=[{"name": "smoothed", "data_type": "float"}],
                )
                new_nodes.append(ma_node)

                # Re-wire: sensor -> MA -> downstream
                new_edges.append(SystemEdge(
                    id=f"signal_edge_{ma_id}_in",
                    source=node_id,
                    source_handle=out_name,
                    target=ma_id,
                    target_handle="value",
                    data_type="float",
                    is_inferred=True,
                ))

                for old_edge in outgoing:
                    remove_ids.add(old_edge.id)
                    new_edges.append(SystemEdge(
                        id=f"signal_edge_{ma_id}_to_{old_edge.target}",
                        source=ma_id,
                        source_handle="smoothed",
                        target=old_edge.target,
                        target_handle=old_edge.target_handle,
                        data_type="float",
                        is_inferred=True,
                    ))

                warnings.append(
                    f"Auto-inserted MovingAverage(window={window_size}) on {node_name}.{out_name}"
                )

        return new_nodes, new_edges, remove_ids, warnings

    # ─── Calibration ─────────────────────────────────────────

    def _insert_calibration(
        self,
        nodes: list[dict],
        edges: list[SystemEdge],
        node_map: dict,
    ) -> tuple[list[InferredNode], list[SystemEdge], set, list[str]]:
        """Insert Calibrator when sensor has calibration config."""
        new_nodes = []
        new_edges = []
        remove_ids = set()
        warnings = []

        for node in nodes:
            config = node.get("configuration", {})
            offset = config.get("calibration_offset")
            scale = config.get("calibration_scale")

            if offset is None and scale is None:
                continue

            node_id = node.get("id", "")
            node_name = node.get("name", node_id)

            # Find outgoing float edges
            outgoing = [
                e for e in edges
                if e.source == node_id and e.data_type in ("float", "any")
            ]

            if not outgoing:
                continue

            cal_id = f"signal_cal_{uuid.uuid4().hex[:8]}"
            cal_node = InferredNode(
                id=cal_id,
                name=f"Calibrate ({node_name})",
                category="control",
                inferred_type="calibrator",
                description=f"Linear calibration for {node_name}",
                reason=f"calibration_offset={offset}, calibration_scale={scale}",
                source_node_id=node_id,
                target_node_id=outgoing[0].target,
                configuration={
                    "offset": float(offset or 0),
                    "scale": float(scale or 1),
                },
                inputs=[{"name": "raw", "data_type": "float"}],
                outputs=[{"name": "calibrated", "data_type": "float"}],
            )
            new_nodes.append(cal_node)

            # Re-wire
            new_edges.append(SystemEdge(
                id=f"signal_edge_{cal_id}_in",
                source=node_id,
                source_handle=outgoing[0].source_handle,
                target=cal_id,
                target_handle="raw",
                data_type="float",
                is_inferred=True,
            ))

            for old_edge in outgoing:
                remove_ids.add(old_edge.id)
                new_edges.append(SystemEdge(
                    id=f"signal_edge_{cal_id}_to_{old_edge.target}",
                    source=cal_id,
                    source_handle="calibrated",
                    target=old_edge.target,
                    target_handle=old_edge.target_handle,
                    data_type="float",
                    is_inferred=True,
                ))

            warnings.append(
                f"Auto-inserted Calibrator(offset={offset or 0}, scale={scale or 1}) on {node_name}"
            )

        return new_nodes, new_edges, remove_ids, warnings

    # ─── Low-Pass Filter ─────────────────────────────────────

    def _insert_low_pass_filter(
        self,
        nodes: list[dict],
        edges: list[SystemEdge],
        node_map: dict,
    ) -> tuple[list[InferredNode], list[SystemEdge], set, list[str]]:
        """Insert LowPassFilter on high-frequency sensor outputs (interval < 500ms)."""
        new_nodes = []
        new_edges = []
        remove_ids = set()
        warnings = []

        for node in nodes:
            if node.get("category") != "sensor":
                continue

            config = node.get("configuration", {})
            interval = config.get("read_interval")

            if interval is None or int(interval) >= 500:
                continue

            node_id = node.get("id", "")
            node_name = node.get("name", node_id)

            # Find outgoing float edges
            outgoing = [
                e for e in edges
                if e.source == node_id and e.data_type in ("float", "any")
            ]

            if not outgoing:
                continue

            lpf_id = f"signal_lpf_{uuid.uuid4().hex[:8]}"
            alpha = 0.3  # Default smoothing factor

            lpf_node = InferredNode(
                id=lpf_id,
                name=f"LPF ({node_name})",
                category="control",
                inferred_type="low_pass_filter",
                description=f"Smooths high-frequency readings from {node_name}",
                reason=f"read_interval={interval}ms is < 500ms, needs smoothing",
                source_node_id=node_id,
                target_node_id=outgoing[0].target,
                configuration={"alpha": alpha},
                inputs=[{"name": "value", "data_type": "float"}],
                outputs=[{"name": "filtered", "data_type": "float"}],
            )
            new_nodes.append(lpf_node)

            new_edges.append(SystemEdge(
                id=f"signal_edge_{lpf_id}_in",
                source=node_id,
                source_handle=outgoing[0].source_handle,
                target=lpf_id,
                target_handle="value",
                data_type="float",
                is_inferred=True,
            ))

            for old_edge in outgoing:
                remove_ids.add(old_edge.id)
                new_edges.append(SystemEdge(
                    id=f"signal_edge_{lpf_id}_to_{old_edge.target}",
                    source=lpf_id,
                    source_handle="filtered",
                    target=old_edge.target,
                    target_handle=old_edge.target_handle,
                    data_type="float",
                    is_inferred=True,
                ))

            warnings.append(
                f"Auto-inserted LowPassFilter(alpha={alpha}) on {node_name} (interval={interval}ms)"
            )

        return new_nodes, new_edges, remove_ids, warnings

    # ─── Unit Conversion ─────────────────────────────────────

    def _insert_unit_conversion(
        self,
        nodes: list[dict],
        edges: list[SystemEdge],
        node_map: dict,
    ) -> tuple[list[InferredNode], list[SystemEdge], set, list[str]]:
        """Insert UnitConverter when source/target units differ."""
        new_nodes = []
        new_edges = []
        remove_ids = set()
        warnings = []

        for edge in edges:
            source = node_map.get(edge.source, {})
            target = node_map.get(edge.target, {})

            source_config = (
                source.get("configuration", {})
                if isinstance(source, dict)
                else getattr(source, "configuration", {})
            )
            target_config = (
                target.get("configuration", {})
                if isinstance(target, dict)
                else getattr(target, "configuration", {})
            )

            source_unit = source_config.get("output_unit", "").lower()
            target_unit = target_config.get("input_unit", "").lower()

            if not source_unit or not target_unit:
                continue
            if source_unit == target_unit:
                continue

            conv_key = (source_unit, target_unit)
            if conv_key not in UNIT_CONVERSIONS:
                continue

            conv_config = UNIT_CONVERSIONS[conv_key]
            uc_id = f"signal_uc_{uuid.uuid4().hex[:8]}"

            source_name = (
                source.get("name", edge.source)
                if isinstance(source, dict)
                else getattr(source, "name", edge.source)
            )

            uc_node = InferredNode(
                id=uc_id,
                name=f"Convert {source_unit}->{target_unit}",
                category="control",
                inferred_type="unit_converter",
                description=f"Convert {source_unit} to {target_unit}",
                reason=f"Unit mismatch: {source_name} outputs {source_unit}, target expects {target_unit}",
                source_node_id=edge.source,
                target_node_id=edge.target,
                configuration=conv_config,
                inputs=[{"name": "value", "data_type": "float"}],
                outputs=[{"name": "converted", "data_type": "float"}],
            )
            new_nodes.append(uc_node)

            remove_ids.add(edge.id)
            new_edges.append(SystemEdge(
                id=f"signal_edge_{uc_id}_in",
                source=edge.source,
                source_handle=edge.source_handle,
                target=uc_id,
                target_handle="value",
                data_type="float",
                is_inferred=True,
            ))
            new_edges.append(SystemEdge(
                id=f"signal_edge_{uc_id}_out",
                source=uc_id,
                source_handle="converted",
                target=edge.target,
                target_handle=edge.target_handle,
                data_type="float",
                is_inferred=True,
            ))

            warnings.append(
                f"Auto-inserted UnitConverter ({source_unit} -> {target_unit}) after {source_name}"
            )

        return new_nodes, new_edges, remove_ids, warnings

    # ─── Helpers ─────────────────────────────────────────────

    def _build_node_map(
        self, originals: list[dict], inferred: list[InferredNode]
    ) -> dict:
        node_map = {}
        for n in originals:
            node_map[n.get("id", "")] = n
        for n in inferred:
            node_map[n.id] = n
        return node_map

    def _topological_sort(
        self, node_ids: list[str], edges: list[SystemEdge]
    ) -> list[str]:
        in_degree = {nid: 0 for nid in node_ids}
        adj = {nid: [] for nid in node_ids}

        for edge in edges:
            if edge.source in adj and edge.target in in_degree:
                adj[edge.source].append(edge.target)
                in_degree[edge.target] += 1

        queue = sorted([nid for nid in node_ids if in_degree[nid] == 0])
        result = []

        while queue:
            node = queue.pop(0)
            result.append(node)
            for neighbor in adj.get(node, []):
                in_degree[neighbor] -= 1
                if in_degree[neighbor] == 0:
                    queue.append(neighbor)
                    queue.sort()

        remaining = [nid for nid in node_ids if nid not in result]
        result.extend(remaining)
        return result
