"""
Block model — represents a hardware or software component on the canvas.
"""

from typing import Optional
from pydantic import BaseModel, Field


class BlockPort(BaseModel):
    """A typed input or output port on a block."""
    name: str
    data_type: str = "any"  # e.g., "float", "bool", "string", "digital", "analog"
    description: str = ""


class BlockConfig(BaseModel):
    """Configuration parameter for a block."""
    key: str
    label: str
    value_type: str = "string"  # "string", "int", "float", "bool", "select"
    default: Optional[str] = None
    options: Optional[list[str]] = None  # For "select" type
    description: str = ""


class Block(BaseModel):
    """A hardware or software block that can be placed on the canvas."""
    id: str
    name: str
    category: str  # "sensor", "communication", "actuator", "logic", "output"
    description: str = ""
    inputs: list[BlockPort] = Field(default_factory=list)
    outputs: list[BlockPort] = Field(default_factory=list)
    configuration: list[BlockConfig] = Field(default_factory=list)
    code_template: str = ""
    icon: str = ""  # Icon identifier for the frontend
    color: str = "#6366f1"  # Default block color


class BlockInstance(BaseModel):
    """An instance of a block placed on the canvas with user-set config."""
    id: str  # Unique instance ID
    block_id: str  # Reference to the block type
    name: str
    category: str
    description: str = ""
    inputs: list[BlockPort] = Field(default_factory=list)
    outputs: list[BlockPort] = Field(default_factory=list)
    configuration: dict = Field(default_factory=dict)  # User-set values
    position: dict = Field(default_factory=lambda: {"x": 0, "y": 0})
