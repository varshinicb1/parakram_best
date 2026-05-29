"""Block metadata schema and population."""

from dataclasses import dataclass, field


@dataclass
class BlockMetadata:
    """Complete metadata for a verified code block in the corpus."""
    block_id: str
    function_name: str
    signature: str
    source_repo: str
    source_file: str
    line_start: int
    line_end: int
    line_count: int
    license: str

    # Correctness
    compiles_clean: bool = False
    warnings_count: int = 0
    ubsan_clean: bool = False
    stack_cost_bytes: int | None = None

    # Semantics
    tags: list[str] = field(default_factory=list)
    peripherals: list[str] = field(default_factory=list)
    target_mcus: list[str] = field(default_factory=list)

    # Dependencies
    includes: list[str] = field(default_factory=list)
    calls: list[str] = field(default_factory=list)

    # Embedding
    embedding_vector: list[float] | None = None
