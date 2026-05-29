"""
Self-Healing Compiler — automatic error fixing via Ollama.

When PlatformIO build fails:
1. Parse compiler error output for file, line, and message
2. Read the failing source file
3. Send error + source + context to Ollama for auto-fix
4. Apply the fix, rebuild
5. Repeat up to N times
"""

import os
import re
import asyncio
from typing import Optional
from agents.llm_provider import get_provider


class CompileError:
    """Parsed compiler error."""
    def __init__(self, file: str, line: int, column: int, message: str, severity: str = "error"):
        self.file = file
        self.line = line
        self.column = column
        self.message = message
        self.severity = severity

    def __repr__(self):
        return f"{self.severity}: {self.file}:{self.line}:{self.column} — {self.message}"


class HealingAttempt:
    """Record of one fix attempt."""
    def __init__(self, attempt: int, errors: list[CompileError], fix_applied: str, success: bool):
        self.attempt = attempt
        self.errors = errors
        self.fix_applied = fix_applied
        self.success = success


class SelfHealingCompiler:
    """Automatically fix compilation errors using Ollama."""

    def __init__(self, max_retries: int = 3):
        self.llm = get_provider()
        self.max_retries = max_retries
        self.attempts: list[HealingAttempt] = []

    async def compile_with_healing(
        self,
        project_dir: str,
        board: str = "esp32dev",
    ) -> dict:
        """
        Compile with automatic error healing.

        Returns:
            {
                "status": "success" | "failed",
                "attempts": int,
                "history": [...],
                "output": str,
            }
        """
        self.attempts = []

        for attempt in range(1, self.max_retries + 1):
            print(f"[SelfHeal] Compile attempt {attempt}/{self.max_retries}")

            # Run PlatformIO build
            result = await self._run_build(project_dir)

            if result["success"]:
                print(f"[SelfHeal] ✅ Build succeeded on attempt {attempt}")
                return {
                    "status": "success",
                    "attempts": attempt,
                    "history": [
                        {
                            "attempt": a.attempt,
                            "errors": [str(e) for e in a.errors],
                            "success": a.success,
                        }
                        for a in self.attempts
                    ],
                    "output": result["output"],
                }

            # Parse errors
            errors = self._parse_errors(result["output"])
            if not errors:
                print("[SelfHeal] Build failed but no parseable errors")
                self.attempts.append(HealingAttempt(attempt, [], "", False))
                continue

            print(f"[SelfHeal] Found {len(errors)} errors, attempting fix...")
            for err in errors[:3]:
                print(f"  → {err}")

            # Try to fix
            fix_applied = await self._fix_errors(errors, project_dir)
            self.attempts.append(HealingAttempt(attempt, errors, fix_applied, False))

            if not fix_applied:
                print("[SelfHeal] Could not generate fix")
                break

        return {
            "status": "failed",
            "attempts": len(self.attempts),
            "history": [
                {
                    "attempt": a.attempt,
                    "errors": [str(e) for e in a.errors],
                    "fix_applied": bool(a.fix_applied),
                    "success": a.success,
                }
                for a in self.attempts
            ],
            "output": result.get("output", ""),
        }

    async def _run_build(self, project_dir: str) -> dict:
        """Run PlatformIO build and capture output."""
        firmware_dir = os.path.join(project_dir, "firmware")
        if not os.path.isdir(firmware_dir):
            return {"success": False, "output": f"Firmware directory not found: {firmware_dir}"}

        try:
            process = await asyncio.create_subprocess_exec(
                "pio", "run",
                cwd=firmware_dir,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.STDOUT,
                env={**os.environ, "PLATFORMIO_FORCE_ANSI": "0"},
            )
            stdout, _ = await asyncio.wait_for(process.communicate(), timeout=120)
            output = stdout.decode("utf-8", errors="replace")

            return {
                "success": process.returncode == 0,
                "output": output,
            }
        except asyncio.TimeoutError:
            return {"success": False, "output": "Build timed out after 120s"}
        except FileNotFoundError:
            return {"success": False, "output": "PlatformIO CLI (pio) not found"}
        except Exception as e:
            return {"success": False, "output": f"Build error: {str(e)}"}

    def _parse_errors(self, output: str) -> list[CompileError]:
        """Parse PlatformIO/GCC error output into structured errors."""
        errors = []
        # GCC error format: file.cpp:line:col: error: message
        pattern = re.compile(
            r'([^\s:]+\.(cpp|h|c|ino)):(\d+):(\d+):\s*(error|warning):\s*(.+)',
            re.IGNORECASE
        )

        for match in pattern.finditer(output):
            errors.append(CompileError(
                file=match.group(1),
                line=int(match.group(3)),
                column=int(match.group(4)),
                message=match.group(6).strip(),
                severity=match.group(5).lower(),
            ))

        # Deduplicate by file+line
        seen = set()
        unique_errors = []
        for err in errors:
            key = f"{err.file}:{err.line}"
            if key not in seen and err.severity == "error":
                seen.add(key)
                unique_errors.append(err)

        return unique_errors

    async def _fix_errors(self, errors: list[CompileError], project_dir: str) -> str:
        """Ask Ollama to fix the compilation errors."""
        if not self.llm.is_available():
            return ""

        # Group errors by file
        file_errors: dict[str, list[CompileError]] = {}
        for err in errors:
            if err.file not in file_errors:
                file_errors[err.file] = []
            file_errors[err.file].append(err)

        fixes_applied = []

        for filepath, errs in file_errors.items():
            # Find the actual file
            actual_path = self._resolve_file(filepath, project_dir)
            if not actual_path or not os.path.exists(actual_path):
                print(f"[SelfHeal] Could not find file: {filepath}")
                continue

            # Read current source
            with open(actual_path, "r", encoding="utf-8", errors="replace") as f:
                source = f.read()

            # Build error description
            error_desc = "\n".join(
                f"Line {e.line}: {e.message}" for e in errs[:5]
            )

            prompt = f"""Fix these compilation errors in this ESP32 Arduino source file.

FILE: {os.path.basename(filepath)}

ERRORS:
{error_desc}

CURRENT SOURCE CODE:
```cpp
{source}
```

Return ONLY the complete fixed source code. No explanations, no markdown fences.
Keep all existing functionality. Only fix the compilation errors."""

            fixed = await self.llm.generate(
                prompt, max_tokens=4000, temperature=0.1
            )

            if fixed and len(fixed) > 30:
                # Clean up
                for fence in ["```cpp", "```c", "```"]:
                    fixed = fixed.replace(fence, "")
                fixed = fixed.strip()

                # Write fixed file
                with open(actual_path, "w", encoding="utf-8") as f:
                    f.write(fixed)

                fixes_applied.append(f"Fixed {len(errs)} errors in {os.path.basename(filepath)}")
                print(f"[SelfHeal] Applied fix to {os.path.basename(filepath)}")

        return "; ".join(fixes_applied)

    def _resolve_file(self, filepath: str, project_dir: str) -> Optional[str]:
        """Resolve a file path from compiler output to actual filesystem path."""
        # Try as-is
        if os.path.exists(filepath):
            return filepath

        # Try relative to firmware directory
        firmware_dir = os.path.join(project_dir, "firmware")
        for subdir in ["src", "include", "lib", "."]:
            candidate = os.path.join(firmware_dir, subdir, os.path.basename(filepath))
            if os.path.exists(candidate):
                return candidate

        # Walk the firmware directory
        basename = os.path.basename(filepath)
        for root, dirs, files in os.walk(firmware_dir):
            if basename in files:
                return os.path.join(root, basename)

        return None
