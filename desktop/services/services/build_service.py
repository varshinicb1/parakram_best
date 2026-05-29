"""
Build Service
Runs PlatformIO CLI to compile firmware with retry logic.
"""

import os
import asyncio
import subprocess
from datetime import datetime


class BuildService:
    """Manages PlatformIO compilation with retry logic."""

    def __init__(self):
        self.projects_dir = os.environ.get("PROJECTS_DIR", "../projects")
        self._build_status: dict[str, dict] = {}
        self.max_default_retries = 5

    async def compile(
        self, project_id: str, max_retries: int = 3
    ) -> dict:
        """
        Compile firmware using PlatformIO CLI.

        Runs `pio run` in the project's firmware directory.
        On failure, captures error output for AI-assisted retry.
        """
        firmware_dir = os.path.join(self.projects_dir, project_id, "firmware")

        if not os.path.exists(os.path.join(firmware_dir, "platformio.ini")):
            return {
                "status": "error",
                "message": "No platformio.ini found. Generate firmware first.",
                "errors": [],
                "output": "",
            }

        self._build_status[project_id] = {
            "status": "compiling",
            "started_at": datetime.now().isoformat(),
            "attempt": 0,
        }

        last_error = ""
        for attempt in range(1, max_retries + 1):
            self._build_status[project_id]["attempt"] = attempt

            result = await self._run_pio_build(firmware_dir)

            if result["success"]:
                self._build_status[project_id] = {
                    "status": "success",
                    "completed_at": datetime.now().isoformat(),
                    "attempt": attempt,
                }
                return {
                    "status": "success",
                    "message": f"Build succeeded on attempt {attempt}",
                    "errors": [],
                    "output": result["output"],
                }

            last_error = result["output"]

            # Log the error for debugging
            self._log_build_error(project_id, attempt, last_error)

            if attempt < max_retries:
                # TODO: Use AI agent to analyze error and fix code
                # For now, just retry
                await asyncio.sleep(1)

        self._build_status[project_id] = {
            "status": "failed",
            "completed_at": datetime.now().isoformat(),
            "attempt": max_retries,
        }

        return {
            "status": "failed",
            "message": f"Build failed after {max_retries} attempts",
            "errors": self._parse_errors(last_error),
            "output": last_error,
        }

    async def _run_pio_build(self, firmware_dir: str) -> dict:
        """Run PlatformIO build command."""
        try:
            process = await asyncio.create_subprocess_exec(
                "pio", "run",
                cwd=firmware_dir,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )
            stdout, stderr = await process.communicate()

            output = stdout.decode("utf-8", errors="replace")
            error_output = stderr.decode("utf-8", errors="replace")

            return {
                "success": process.returncode == 0,
                "output": output + error_output,
            }
        except FileNotFoundError:
            return {
                "success": False,
                "output": "PlatformIO CLI not found. Install with: pip install platformio",
            }
        except Exception as e:
            return {
                "success": False,
                "output": f"Build error: {str(e)}",
            }

    def _parse_errors(self, output: str) -> list[str]:
        """Extract error messages from compiler output."""
        errors = []
        for line in output.split("\n"):
            if "error:" in line.lower():
                errors.append(line.strip())
        return errors

    def _log_build_error(self, project_id: str, attempt: int, error: str):
        """Log build error to project logs."""
        log_dir = os.path.join(self.projects_dir, project_id, "logs")
        os.makedirs(log_dir, exist_ok=True)

        log_file = os.path.join(log_dir, f"build_attempt_{attempt}.log")
        with open(log_file, "w") as f:
            f.write(f"Build Attempt {attempt}\n")
            f.write(f"Timestamp: {datetime.now().isoformat()}\n")
            f.write("=" * 60 + "\n")
            f.write(error)

    def get_status(self, project_id: str) -> dict:
        """Get current build status."""
        return self._build_status.get(project_id, {"status": "idle"})
