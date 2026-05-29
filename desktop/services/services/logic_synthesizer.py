"""
Logic Synthesizer -- generates logical control structures automatically.

Runs after the System Planner, operating on SystemGraph.
Detects multi-input patterns, feedback loops, and oscillation-prone
edges, inserting AND/OR combinators, hysteresis blocks, and PID
controllers as needed.

Pipeline step: SystemGraph (planned) -> SystemGraph (synthesized)
"""

import uuid
from models.system_models import SystemGraph, SystemEdge, InferredNode


# ─── Synthesis Rules ─────────────────────────────────────────

COMBINATOR_RULES = {
    "all_bool": {
        "block_id": "and_combinator",
        "name": "AND Gate",
        "description": "All boolean inputs must be true",
        "output_type": "bool",
    },
    "any_bool": {
        "block_id": "or_combinator",
        "name": "OR Gate",
        "description": "Any boolean input triggers output",
        "output_type": "bool",
    },
    "all_float": {
        "block_id": "weighted_average",
        "name": "Weighted Average",
        "description": "Combine multiple float readings",
        "output_type": "float",
    },
}


class LogicSynthesizer:
    """
    Generates logical control structures from graph patterns.

    Detects:
    1. N sensors -> 1 actuator: insert AND/OR/WeightedAverage combinator
    2. Threshold with oscillation risk: replace with hysteresis
    3. Actuator -> sensor feedback loop: insert PID controller
    """

    def synthesize(self, system_graph: SystemGraph) -> SystemGraph:
        """
        Main entry point. Analyze system graph and insert control logic.
        Returns a new SystemGraph with additional inferred nodes.
        """
        all_original = list(system_graph.original_nodes)
        all_inferred = list(system_graph.inferred_nodes)
        all_edges = list(system_graph.edges)
        warnings = list(system_graph.warnings)

        # Build lookup maps
        node_map = self._build_node_map(all_original, all_inferred)

        # Phase 1: Detect multi-input actuators
        new_nodes_1, new_edges_1, remove_1, warns_1 = (
            self._detect_multi_input_actuator(all_original, all_inferred, all_edges, node_map)
        )
        all_inferred.extend(new_nodes_1)
        all_edges = [e for e in all_edges if e.id not in remove_1]
        all_edges.extend(new_edges_1)
        warnings.extend(warns_1)

        # Phase 2: Detect hysteresis needs
        new_nodes_2, new_edges_2, remove_2, warns_2 = (
            self._detect_hysteresis_need(all_inferred, all_edges, node_map)
        )
        # Replace threshold nodes with hysteresis where applicable
        all_inferred = [n for n in all_inferred if n.id not in remove_2]
        all_inferred.extend(new_nodes_2)
        all_edges = [e for e in all_edges if e.id not in remove_2]
        all_edges.extend(new_edges_2)
        warnings.extend(warns_2)

        # Phase 3: Detect feedback loops (PID insertion)
        new_nodes_3, new_edges_3, remove_3, warns_3 = (
            self._detect_feedback_loop(all_original, all_edges, node_map)
        )
        all_inferred.extend(new_nodes_3)
        all_edges = [e for e in all_edges if e.id not in remove_3]
        all_edges.extend(new_edges_3)
        warnings.extend(warns_3)

        # Rebuild node map and topological sort
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

    # ─── Multi-Input Actuator Detection ──────────────────────

    def _detect_multi_input_actuator(
        self,
        original_nodes: list[dict],
        inferred_nodes: list[InferredNode],
        edges: list[SystemEdge],
        node_map: dict,
    ) -> tuple[list[InferredNode], list[SystemEdge], set, list[str]]:
        """
        Find actuators with multiple incoming edges and insert combinators.
        """
        new_nodes = []
        new_edges = []
        remove_edge_ids = set()
        warnings = []

        # Count incoming edges per target node
        target_sources: dict[str, list[SystemEdge]] = {}
        for edge in edges:
            if edge.target not in target_sources:
                target_sources[edge.target] = []
            target_sources[edge.target].append(edge)

        for target_id, incoming in target_sources.items():
            if len(incoming) < 2:
                continue

            target_node = node_map.get(target_id, {})
            target_category = (
                target_node.get("category", "")
                if isinstance(target_node, dict)
                else getattr(target_node, "category", "")
            )

            # Only synthesize for actuators/output
            if target_category not in ("actuator", "output"):
                continue

            # Determine input types
            source_types = set()
            for edge in incoming:
                source_types.add(edge.data_type)

            # Select combinator based on input types
            bool_types = {"bool", "digital"}
            float_types = {"float", "int", "analog"}

            if source_types <= bool_types:
                rule = COMBINATOR_RULES["all_bool"]
            elif source_types <= float_types:
                rule = COMBINATOR_RULES["all_float"]
            elif source_types & bool_types:
                rule = COMBINATOR_RULES["any_bool"]
            else:
                continue

            # Create combinator node
            node_id = f"synth_{rule['block_id']}_{uuid.uuid4().hex[:8]}"
            target_name = (
                target_node.get("name", target_id)
                if isinstance(target_node, dict)
                else getattr(target_node, "name", target_id)
            )

            combinator = InferredNode(
                id=node_id,
                name=f"{rule['name']} (-> {target_name})",
                category="control",
                inferred_type=rule["block_id"],
                description=rule["description"],
                reason=f"{len(incoming)} inputs to {target_name} need combining",
                source_node_id=incoming[0].source,
                target_node_id=target_id,
                configuration={"input_count": len(incoming)},
                inputs=[
                    {"name": f"input_{i+1}", "data_type": e.data_type}
                    for i, e in enumerate(incoming)
                ],
                outputs=[{"name": "result", "data_type": rule["output_type"]}],
            )
            new_nodes.append(combinator)

            # Re-wire: all source edges -> combinator, combinator -> target
            for i, old_edge in enumerate(incoming):
                remove_edge_ids.add(old_edge.id)
                new_edges.append(SystemEdge(
                    id=f"synth_edge_{node_id}_in_{i}",
                    source=old_edge.source,
                    source_handle=old_edge.source_handle,
                    target=node_id,
                    target_handle=f"input_{i+1}",
                    data_type=old_edge.data_type,
                    is_inferred=True,
                ))

            # Combinator -> target
            new_edges.append(SystemEdge(
                id=f"synth_edge_{node_id}_out",
                source=node_id,
                source_handle="result",
                target=target_id,
                target_handle=incoming[0].target_handle,
                data_type=rule["output_type"],
                is_inferred=True,
            ))

            warnings.append(
                f"Synthesized '{rule['name']}' for {len(incoming)} inputs to '{target_name}'"
            )

        return new_nodes, new_edges, remove_edge_ids, warnings

    # ─── Hysteresis Detection ────────────────────────────────

    def _detect_hysteresis_need(
        self,
        inferred_nodes: list[InferredNode],
        edges: list[SystemEdge],
        node_map: dict,
    ) -> tuple[list[InferredNode], list[SystemEdge], set, list[str]]:
        """
        Find threshold nodes that could oscillate and upgrade to hysteresis.
        """
        new_nodes = []
        new_edges = []
        remove_ids = set()
        warnings = []

        for node in inferred_nodes:
            if node.inferred_type != "threshold":
                continue

            threshold_val = node.configuration.get("threshold", 30.0)

            # Create hysteresis replacement
            hyst_id = f"synth_hysteresis_{uuid.uuid4().hex[:8]}"
            hysteresis = InferredNode(
                id=hyst_id,
                name=f"Hysteresis ({node.source_node_id} -> {node.target_node_id})",
                category="control",
                inferred_type="hysteresis",
                description="Prevents output oscillation near threshold",
                reason=f"Upgraded from threshold ({threshold_val}) to prevent rapid toggling",
                source_node_id=node.source_node_id,
                target_node_id=node.target_node_id,
                configuration={
                    "high_threshold": float(threshold_val),
                    "low_threshold": float(threshold_val) * 0.85,
                },
                inputs=list(node.inputs),
                outputs=list(node.outputs),
            )
            new_nodes.append(hysteresis)
            remove_ids.add(node.id)

            # Re-wire edges that referenced the old threshold node
            for edge in edges:
                if edge.target == node.id:
                    new_edges.append(SystemEdge(
                        id=f"synth_edge_{hyst_id}_in",
                        source=edge.source,
                        source_handle=edge.source_handle,
                        target=hyst_id,
                        target_handle="value",
                        data_type=edge.data_type,
                        is_inferred=True,
                    ))
                    remove_ids.add(edge.id)
                elif edge.source == node.id:
                    new_edges.append(SystemEdge(
                        id=f"synth_edge_{hyst_id}_out",
                        source=hyst_id,
                        source_handle="active",
                        target=edge.target,
                        target_handle=edge.target_handle,
                        data_type="bool",
                        is_inferred=True,
                    ))
                    remove_ids.add(edge.id)

            warnings.append(
                f"Upgraded threshold to hysteresis: "
                f"ON>{threshold_val}, OFF<{float(threshold_val) * 0.85:.1f}"
            )

        return new_nodes, new_edges, remove_ids, warnings

    # ─── Feedback Loop Detection (PID) ───────────────────────

    def _detect_feedback_loop(
        self,
        original_nodes: list[dict],
        edges: list[SystemEdge],
        node_map: dict,
    ) -> tuple[list[InferredNode], list[SystemEdge], set, list[str]]:
        """
        Detect actuator -> sensor feedback loops and insert PID controller.
        """
        new_nodes = []
        new_edges = []
        remove_ids = set()
        warnings = []

        # Build adjacency for cycle detection
        adjacency: dict[str, list[str]] = {}
        for edge in edges:
            if edge.source not in adjacency:
                adjacency[edge.source] = []
            adjacency[edge.source].append(edge.target)

        # Find actuator nodes
        actuators = [
            n for n in original_nodes
            if n.get("category") == "actuator"
        ]

        for actuator in actuators:
            act_id = actuator.get("id", "")
            # Check if any downstream path leads back to an upstream sensor
            visited = set()
            queue = list(adjacency.get(act_id, []))

            while queue:
                current = queue.pop(0)
                if current in visited:
                    continue
                visited.add(current)

                current_node = node_map.get(current, {})
                current_cat = (
                    current_node.get("category", "")
                    if isinstance(current_node, dict)
                    else getattr(current_node, "category", "")
                )

                # Found a sensor that feeds into this actuator's upstream chain?
                if current_cat == "sensor":
                    # Check if this sensor has an edge leading to a path toward the actuator
                    sensor_downstreams = adjacency.get(current, [])
                    for downstream in sensor_downstreams:
                        # See if downstream eventually reaches our actuator
                        if self._can_reach(downstream, act_id, adjacency):
                            # Found feedback loop: sensor -> ... -> actuator -> ... -> sensor
                            pid_id = f"synth_pid_{uuid.uuid4().hex[:8]}"
                            act_name = actuator.get("name", act_id)
                            sensor_name = (
                                current_node.get("name", current)
                                if isinstance(current_node, dict)
                                else getattr(current_node, "name", current)
                            )

                            pid = InferredNode(
                                id=pid_id,
                                name=f"PID ({sensor_name} -> {act_name})",
                                category="control",
                                inferred_type="pid_controller",
                                description=f"Closed-loop control for {act_name}",
                                reason=f"Feedback loop: {sensor_name} -> ... -> {act_name} -> ... -> {sensor_name}",
                                source_node_id=current,
                                target_node_id=act_id,
                                configuration={
                                    "kp": 1.0, "ki": 0.1, "kd": 0.05,
                                    "setpoint": 25.0,
                                    "output_min": 0, "output_max": 100,
                                },
                                inputs=[
                                    {"name": "measurement", "data_type": "float"},
                                    {"name": "setpoint", "data_type": "float"},
                                ],
                                outputs=[
                                    {"name": "output", "data_type": "float"},
                                    {"name": "error", "data_type": "float"},
                                ],
                            )
                            new_nodes.append(pid)
                            warnings.append(
                                f"Synthesized PID controller for feedback loop: "
                                f"{sensor_name} <-> {act_name}"
                            )
                            break  # One PID per actuator

                queue.extend(adjacency.get(current, []))

        return new_nodes, new_edges, remove_ids, warnings

    # ─── Helpers ─────────────────────────────────────────────

    def _build_node_map(
        self, originals: list[dict], inferred: list[InferredNode]
    ) -> dict:
        """Build a unified node lookup map."""
        node_map = {}
        for n in originals:
            node_map[n.get("id", "")] = n
        for n in inferred:
            node_map[n.id] = n
        return node_map

    def _can_reach(
        self, start: str, target: str, adjacency: dict[str, list[str]]
    ) -> bool:
        """BFS check if target is reachable from start."""
        visited = set()
        queue = [start]
        while queue:
            current = queue.pop(0)
            if current == target:
                return True
            if current in visited:
                continue
            visited.add(current)
            queue.extend(adjacency.get(current, []))
        return False

    def _topological_sort(
        self, node_ids: list[str], edges: list[SystemEdge]
    ) -> list[str]:
        """Kahn's algorithm topological sort."""
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
