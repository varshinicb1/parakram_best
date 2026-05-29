"""Post-synthesis verification pipeline."""

from dataclasses import dataclass

from firmware.composer import FirmwareProject


@dataclass
class VerificationResult:
    """Result of verifying a generated firmware project."""
    compiles: bool
    warnings: list[str]
    errors: list[str]
    stack_usage_bytes: int
    flash_usage_bytes: int
    meets_constraints: bool


def verify_firmware(project: FirmwareProject) -> VerificationResult:
    """Verify a generated firmware project.

    Checks:
      1. Syntax check (gcc -fsyntax-only)
      2. Stack usage analysis
      3. Flash size estimation
      4. Constraint verification (fits in target MCU resources)
    """
    from corpus.ingest.validator import compile_block

    result = compile_block(project.main_c, project.includes, project.target_mcu)

    from config import TARGET_MCUS
    mcu = TARGET_MCUS.get(project.target_mcu, {})
    max_flash = mcu.get("flash_kb", 0) * 1024
    max_ram = mcu.get("sram_kb", 0) * 1024

    estimated_flash = project.estimated_flash_kb * 1024
    estimated_ram = project.estimated_ram_kb * 1024

    meets = (
        result.compiles and
        estimated_flash < max_flash and
        estimated_ram < max_ram
    )

    return VerificationResult(
        compiles=result.compiles,
        warnings=result.warnings,
        errors=result.errors,
        stack_usage_bytes=result.stack_cost_bytes or 0,
        flash_usage_bytes=estimated_flash,
        meets_constraints=meets,
    )
