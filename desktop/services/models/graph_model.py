"""
Graph model — represents the canvas state (nodes + edges).
"""

from typing import Optional
from pydantic import BaseModel, Field


class GraphNode(BaseModel):
    """A node on the canvas — wraps a BlockInstance with position data."""
    id: str
    block_id: str  # Which block type this is
    name: str
    category: str
    description: str = ""
    position: dict = Field(default_factory=lambda: {"x": 0, "y": 0})
    configuration: dict = Field(default_factory=dict)
    inputs: list[dict] = Field(default_factory=list)
    outputs: list[dict] = Field(default_factory=list)


class GraphEdge(BaseModel):
    """A connection between two block ports."""
    id: str
    source: str  # Source node ID
    source_handle: str  # Source port name
    target: str  # Target node ID
    target_handle: str  # Target port name
    data_type: str = "any"


class CanvasGraph(BaseModel):
    """The complete canvas state."""
    nodes: list[GraphNode] = Field(default_factory=list)
    edges: list[GraphEdge] = Field(default_factory=list)


class ProjectMeta(BaseModel):
    """Project metadata."""
    id: str
    name: str
    description: str = ""
    target_board: str = "esp32"
    framework: str = "arduino"
    created_at: str = ""
    updated_at: str = ""
    version: int = 1
