"""Compilation + static analysis pipeline for extracted blocks."""

import subprocess
import tempfile
from dataclasses import dataclass
from pathlib import Path

from config import COMPILATION_TIMEOUT_SECONDS, TARGET_MCUS


@dataclass
class ValidationResult:
    """Result of validating a single code block."""
    block_id: str
    compiles: bool
    warnings: list[str]
    errors: list[str]
    stack_cost_bytes: int | None
    has_undefined_behavior: bool
    static_analysis_issues: list[str]


def compile_block(
    source: str,
    includes: list[str],
    target: str = "esp32s3",
) -> ValidationResult:
    """Attempt to compile a code block and run static analysis."""
    mcu = TARGET_MCUS.get(target)
    if not mcu:
        return ValidationResult("", False, [], [f"Unknown target: {target}"], None, False, [])

    with tempfile.NamedTemporaryFile(suffix=".c", mode="w", delete=False) as f:
        # Write includes
        for inc in includes:
            f.write(f"#include <{inc}>\n")
        f.write("\n")
        f.write(source)
        f.flush()
        src_path = Path(f.name)

    warnings: list[str] = []
    errors: list[str] = []

    # Try compile with GCC
    try:
        result = subprocess.run(
            [
                "gcc", "-fsyntax-only", "-Wall", "-Wextra", "-Wpedantic",
                "-std=c11", str(src_path),
            ],
            capture_output=True,
            text=True,
            timeout=COMPILATION_TIMEOUT_SECONDS,
        )
        if result.returncode != 0:
            for line in result.stderr.splitlines():
                if "warning:" in line:
                    warnings.append(line)
                elif "error:" in line:
                    errors.append(line)
        compiles = result.returncode == 0
    except FileNotFoundError:
        compiles = False
        errors.append("gcc not found")
    except subprocess.TimeoutExpired:
        compiles = False
        errors.append("compilation timeout")
    finally:
        src_path.unlink(missing_ok=True)

    # Static analysis with cppcheck
    static_issues: list[str] = []
    try:
        with tempfile.NamedTemporaryFile(suffix=".c", mode="w", delete=False) as f2:
            f2.write(source)
            f2.flush()
            cp_result = subprocess.run(
                ["cppcheck", "--enable=warning,style", "--quiet", f2.name],
                capture_output=True, text=True, timeout=30,
            )
            static_issues = [l for l in cp_result.stderr.splitlines() if l.strip()]
            Path(f2.name).unlink(missing_ok=True)
    except (FileNotFoundError, subprocess.TimeoutExpired):
        pass

    return ValidationResult(
        block_id="",
        compiles=compiles,
        warnings=warnings,
        errors=errors,
        stack_cost_bytes=None,
        has_undefined_behavior=len(static_issues) > 0,
        static_analysis_issues=static_issues,
    )


def validate_corpus() -> dict[str, int]:
    """Validate all blocks in the corpus. Returns counts."""
    # Placeholder — full implementation would iterate DB blocks
    return {"valid": 0, "invalid": 0, "skipped": 0}
