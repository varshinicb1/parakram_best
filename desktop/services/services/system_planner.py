"""
System Planner — interprets block graphs and infers control logic.

Analyzes the canvas graph and automatically inserts missing logic nodes
when detecting common embedded system patterns (e.g., sensor + pump
without threshold logic → auto-insert threshold).

Pipeline step: CanvasGraph → SystemGraph
"""

import uuid
from models.graph_model import CanvasGraph, GraphNode, GraphEdge
from models.system_models import (
    SystemGraph,
    SystemEdge,
    InferredNode,
)


# ─── Inference Pattern Rules ─────────────────────────────────

INFERENCE_RULES = [
    {
        "name": "threshold_insertion",
        "description": "Sensor float → Actuator bool needs threshold comparison",
        "source_categories": ["sensor"],
        "target_categories": ["actuator"],
        "source_output_types": ["float", "int", "analog"],
        "target_input_types": ["bool", "digital"],
        "inferred_type": "threshold",
        "inferred_name": "Auto Threshold",
        "default_config": {"threshold": 30.0, "comparison": "greater_than"},
    },
    {
        "name": "formatter_insertion",
        "description": "Sensor data → Communication needs serialization",
        "source_categories": ["sensor"],
        "target_categories": ["communication"],
        "source_output_types": ["float", "int", "analog"],
        "target_input_types": ["string", "any"],
        "inferred_type": "formatter",
        "inferred_name": "Data Formatter",
        "default_config": {"format": "json", "precision": 2},
    },
    {
        "name": "debounce_insertion",
        "description": "Digital input → Actuator needs debounce filter",
        "source_categories": ["sensor"],
        "target_categories": ["actuator"],
        "source_output_types": ["digital", "bool"],
        "target_input_types": ["bool", "digital"],
        "inferred_type": "debounce",
        "inferred_name": "Debounce Filter",
        "default_config": {"delay_ms": 50, "trigger": "rising"},
    },
    {
        "name": "value_mapper_insertion",
        "description": "Sensor range → Actuator range needs value mapping",
        "source_categories": ["sensor"],
        "target_categories": ["actuator"],
        "source_output_types": ["float", "int", "analog"],
        "target_input_types": ["float", "int", "analog"],
        "inferred_type": "mapper",
        "inferred_name": "Value Mapper",
        "default_config": {
            "input_min": 0, "input_max": 100,
            "output_min": 0, "output_max": 180,
        },
    },
]


class SystemPlanner:
    """
    Interprets block graphs and infers missing control logic.

    Given a canvas graph, the planner:
    1. Detects patterns that need intermediate logic
    2. Auto-inserts inferred nodes (threshold, formatter, debounce, mapper)
    3. Re-wires edges through the inferred nodes
    4. Validates data type compatibility
    5. Returns a topologically-sorted SystemGraph
    """

    def plan(self, canvas: CanvasGraph) -> SystemGraph:
        """
        Main entry point. Analyze canvas graph and produce enriched SystemGraph.
        """
        warnings = []
        data_type_errors = []

        # Convert original nodes to dicts for the system graph
        original_nodes = [node.model_dump() for node in canvas.nodes]
        original_edges = [edge.model_dump() for edge in canvas.edges]

        # Build lookup maps
        node_map = {node.id: node for node in canvas.nodes}

        # Detect patterns and infer missing nodes
        inferred_nodes = []
        new_edges = []
        edges_to_remove = set()

        for edge in canvas.edges:
            source_node = node_map.get(edge.source)
            target_node = node_map.get(edge.target)

            if not source_node or not target_node:
                warnings.append(
                    f"Edge {edge.id}: dangling reference "
                    f"(source={edge.source}, target={edge.target})"
                )
                continue

            # Check if pattern inference applies
            rule = self._match_rule(source_node, target_node, edge)
            if rule:
                # Auto-insert an inferred node
                inferred, new_edge_pair = self._create_inferred_node(
                    rule, source_node, target_node, edge
                )
                inferred_nodes.append(inferred)
                new_edges.extend(new_edge_pair)
                edges_to_remove.add(edge.id)
                warnings.append(
                    f"Auto-inserted '{inferred.name}' between "
                    f"'{source_node.name}' and '{target_node.name}' — "
                    f"{rule['description']}"
                )

        # Validate data types on remaining edges
        for edge in canvas.edges:
            if edge.id in edges_to_remove:
                continue
            type_error = self._check_data_type(edge, node_map)
            if type_error:
                data_type_errors.append(type_error)

        # Build final edge list: original (minus removed) + new inferred edges
        final_edges = []
        for edge in canvas.edges:
            if edge.id not in edges_to_remove:
                final_edges.append(SystemEdge(
                    id=edge.id,
                    source=edge.source,
                    source_handle=edge.source_handle,
                    target=edge.target,
                    target_handle=edge.target_handle,
                    data_type=edge.data_type,
                    is_inferred=False,
                ))
        final_edges.extend(new_edges)

        # Build combined node list for topological sort
        all_node_ids = [n["id"] for n in original_nodes] + [n.id for n in inferred_nodes]
        execution_order = self._topological_sort(all_node_ids, final_edges)

        return SystemGraph(
            original_nodes=original_nodes,
            inferred_nodes=inferred_nodes,
            edges=final_edges,
            execution_order=execution_order,
            warnings=warnings,
            data_type_errors=data_type_errors,
        )

    def _match_rule(
        self, source: GraphNode, target: GraphNode, edge: GraphEdge
    ) -> dict | None:
        """Check if an edge matches any inference rule."""
        # Skip if target is already a logic node (user already added logic)
        if target.category == "logic":
            return None

        # Skip if source is a logic node (already has processing)
        if source.category == "logic":
            return None

        # Find source output type from the edge handle
        source_output_type = self._get_port_type(source.outputs, edge.source_handle)
        target_input_type = self._get_port_type(target.inputs, edge.target_handle)

        for rule in INFERENCE_RULES:
            if (
                source.category in rule["source_categories"]
                and target.category in rule["target_categories"]
                and source_output_type in rule["source_output_types"]
                and target_input_type in rule["target_input_types"]
            ):
                return rule

        return None

    def _get_port_type(self, ports: list[dict], handle_name: str) -> str:
        """Get the data_type of a port by handle name."""
        for port in ports:
            name = port.get("name", "") if isinstance(port, dict) else getattr(port, "name", "")
            if name == handle_name:
                return port.get("data_type", "any") if isinstance(port, dict) else getattr(port, "data_type", "any")
        return "any"

    def _create_inferred_node(
        self, rule: dict, source: GraphNode, target: GraphNode, edge: GraphEdge
    ) -> tuple[InferredNode, list[SystemEdge]]:
        """Create an inferred node and the edges connecting it."""
        node_id = f"inferred_{rule['inferred_type']}_{uuid.uuid4().hex[:8]}"

        # Determine I/O types based on the rule
        source_type = self._get_port_type(source.outputs, edge.source_handle)
        target_type = self._get_port_type(target.inputs, edge.target_handle)

        inferred = InferredNode(
            id=node_id,
            name=f"{rule['inferred_name']} ({source.name} → {target.name})",
            category="logic",
            inferred_type=rule["inferred_type"],
            description=rule["description"],
            reason=f"Pattern detected: {source.category}.{source_type} → {target.category}.{target_type}",
            source_node_id=source.id,
            target_node_id=target.id,
            configuration=rule["default_config"].copy(),
            inputs=[{"name": "value", "data_type": source_type}],
            outputs=[{"name": "result", "data_type": target_type}],
        )

        # Edge: source → inferred node
        edge_in = SystemEdge(
            id=f"inferred_edge_{node_id}_in",
            source=source.id,
            source_handle=edge.source_handle,
            target=node_id,
            target_handle="value",
            data_type=source_type,
            is_inferred=True,
        )

        # Edge: inferred node → target
        edge_out = SystemEdge(
            id=f"inferred_edge_{node_id}_out",
            source=node_id,
            source_handle="result",
            target=target.id,
            target_handle=edge.target_handle,
            data_type=target_type,
            is_inferred=True,
        )

        return inferred, [edge_in, edge_out]

    def _check_data_type(
        self, edge: GraphEdge, node_map: dict[str, GraphNode]
    ) -> str | None:
        """Check if source output type matches target input type."""
        source = node_map.get(edge.source)
        target = node_map.get(edge.target)

        if not source or not target:
            return None

        source_type = self._get_port_type(source.outputs, edge.source_handle)
        target_type = self._get_port_type(target.inputs, edge.target_handle)

        # "any" is always compatible
        if source_type == "any" or target_type == "any":
            return None

        # Same type is compatible
        if source_type == target_type:
            return None

        # Numeric types are compatible
        numeric = {"float", "int", "analog"}
        if source_type in numeric and target_type in numeric:
            return None

        # Boolean/digital are compatible
        boolean = {"bool", "digital"}
        if source_type in boolean and target_type in boolean:
            return None

        return (
            f"Type mismatch on edge '{edge.id}': "
            f"{source.name}.{edge.source_handle} ({source_type}) → "
            f"{target.name}.{edge.target_handle} ({target_type})"
        )

    def _topological_sort(
        self, node_ids: list[str], edges: list[SystemEdge]
    ) -> list[str]:
        """Topological sort using Kahn's algorithm."""
        # Build adjacency list and in-degree count
        in_degree = {nid: 0 for nid in node_ids}
        adjacency = {nid: [] for nid in node_ids}

        for edge in edges:
            if edge.source in adjacency and edge.target in in_degree:
                adjacency[edge.source].append(edge.target)
                in_degree[edge.target] += 1

        # Start with nodes that have no incoming edges
        queue = [nid for nid in node_ids if in_degree[nid] == 0]
        result = []

        while queue:
            # Sort for deterministic output
            queue.sort()
            node = queue.pop(0)
            result.append(node)

            for neighbor in adjacency.get(node, []):
                in_degree[neighbor] -= 1
                if in_degree[neighbor] == 0:
                    queue.append(neighbor)

        # If we didn't process all nodes, there's a cycle
        if len(result) < len(node_ids):
            remaining = [nid for nid in node_ids if nid not in result]
            result.extend(remaining)  # Append cyclics at the end

        return result
