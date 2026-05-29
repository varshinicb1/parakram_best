"""
Wokwi Verification Service — compiles firmware and runs Wokwi simulation
to verify the generated code actually works.

Pipeline:
1. Resolve PlatformIO library dependencies
2. Compile firmware via PlatformIO
3. Generate Wokwi diagram.json from block graph
4. Run Wokwi simulation and monitor serial output
5. Check for crashes, assertion failures, and expected output
"""

import os
import json
import asyncio
from typing import Optional

from services.lib_resolver import resolve_and_update
from services.self_healing_compiler import SelfHealingCompiler
from api.wokwi_routes import generate_diagram


class VerificationResult:
    """Result of a firmware verification run."""
    def __init__(self):
        self.compile_success = False
        self.compile_attempts = 0
        self.compile_output = ""
        self.lib_deps_resolved: list[str] = []
        self.simulation_ran = False
        self.simulation_output = ""
        self.simulation_passed = False
        self.errors: list[str] = []
        self.warnings: list[str] = []

    def to_dict(self) -> dict:
        return {
            "status": "pass" if self.compile_success else "fail",
            "compile": {
                "success": self.compile_success,
                "attempts": self.compile_attempts,
                "output_snippet": self.compile_output[-500:] if self.compile_output else "",
            },
            "libraries": self.lib_deps_resolved,
            "simulation": {
                "ran": self.simulation_ran,
                "passed": self.simulation_passed,
                "output_snippet": self.simulation_output[-500:] if self.simulation_output else "",
            },
            "errors": self.errors,
            "warnings": self.warnings,
        }


class FirmwareVerifier:
    """End-to-end firmware verification: compile -> simulate -> check."""

    def __init__(self, max_compile_retries: int = 3):
        self.healer = SelfHealingCompiler(max_retries=max_compile_retries)

    async def verify(
        self,
        project_dir: str,
        nodes: list[dict] = None,
        edges: list[dict] = None,
        board: str = "esp32dev",
        run_simulation: bool = True,
    ) -> VerificationResult:
        """
        Full verification pipeline:
        1. Auto-resolve library deps
        2. Compile with self-healing
        3. Optionally run Wokwi simulation
        """
        result = VerificationResult()

        # ── Step 1: Resolve library dependencies ────────
        print("[Verify] Step 1: Resolving library dependencies...")
        try:
            lib_result = await resolve_and_update(project_dir)
            result.lib_deps_resolved = lib_result.get("lib_deps", [])
            if result.lib_deps_resolved:
                print(f"[Verify] Added {len(result.lib_deps_resolved)} lib_deps to platformio.ini")
        except Exception as e:
            result.warnings.append(f"Library resolution failed: {e}")

        # ── Step 2: Compile with self-healing ───────────
        print("[Verify] Step 2: Compiling with self-healing...")
        try:
            compile_result = await self.healer.compile_with_healing(
                project_dir=project_dir,
                board=board,
            )
            result.compile_success = compile_result.get("status") == "success"
            result.compile_attempts = compile_result.get("attempts", 0)
            result.compile_output = compile_result.get("output", "")

            if not result.compile_success:
                # Extract errors from history
                for attempt in compile_result.get("history", []):
                    for err in attempt.get("errors", []):
                        result.errors.append(str(err))
                print(f"[Verify] Compile FAILED after {result.compile_attempts} attempts")
                return result
            else:
                print(f"[Verify] Compile OK (attempt {result.compile_attempts})")
        except Exception as e:
            result.errors.append(f"Compile error: {e}")
            return result

        # ── Step 3: Generate Wokwi diagram ──────────────
        if run_simulation and nodes:
            print("[Verify] Step 3: Generating Wokwi diagram...")
            try:
                diagram = generate_diagram(nodes or [], edges or [])
                diagram_path = os.path.join(project_dir, "firmware", "diagram.json")
                with open(diagram_path, "w") as f:
                    json.dump(diagram, f, indent=2)

                # Also create wokwi.toml
                wokwi_toml = f"""[wokwi]
version = 1
firmware = ".pio/build/{board}/firmware.bin"
elf = ".pio/build/{board}/firmware.elf"
"""
                with open(os.path.join(project_dir, "firmware", "wokwi.toml"), "w") as f:
                    f.write(wokwi_toml)

                print(f"[Verify] Diagram: {len(diagram['parts'])} parts, {len(diagram['connections'])} wires")
            except Exception as e:
                result.warnings.append(f"Diagram generation failed: {e}")

        # ── Step 4: Run Wokwi simulation ────────────────
        if run_simulation and result.compile_success:
            print("[Verify] Step 4: Running Wokwi simulation...")
            try:
                sim_result = await self._run_wokwi(project_dir, board, timeout=15)
                result.simulation_ran = True
                result.simulation_output = sim_result.get("output", "")
                result.simulation_passed = sim_result.get("passed", False)

                if result.simulation_passed:
                    print("[Verify] Simulation PASSED")
                else:
                    print(f"[Verify] Simulation completed (check output)")
                    if sim_result.get("errors"):
                        result.warnings.extend(sim_result["errors"])
            except Exception as e:
                result.warnings.append(f"Simulation skipped: {e}")
                # Simulation failure is a warning, not a hard error
                result.simulation_ran = False

        return result

    async def _run_wokwi(
        self, project_dir: str, board: str, timeout: int = 15
    ) -> dict:
        """Run Wokwi simulation and capture serial output."""
        firmware_dir = os.path.join(project_dir, "firmware")

        # Check for wokwi.toml and diagram.json
        if not os.path.exists(os.path.join(firmware_dir, "wokwi.toml")):
            return {"output": "", "passed": False, "errors": ["No wokwi.toml"]}
        if not os.path.exists(os.path.join(firmware_dir, "diagram.json")):
            return {"output": "", "passed": False, "errors": ["No diagram.json"]}

        # Check for compiled firmware
        bin_path = os.path.join(firmware_dir, ".pio", "build", board, "firmware.bin")
        if not os.path.exists(bin_path):
            return {"output": "", "passed": False, "errors": ["No firmware.bin — compile first"]}

        try:
            # Run wokwi-cli if available
            process = await asyncio.create_subprocess_exec(
                "wokwi-cli", "--timeout", str(timeout * 1000),
                cwd=firmware_dir,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.STDOUT,
            )
            stdout, _ = await asyncio.wait_for(
                process.communicate(), timeout=timeout + 10
            )
            output = stdout.decode("utf-8", errors="replace")

            # Check for common failure patterns
            passed = True
            errors = []
            failure_patterns = [
                "Guru Meditation Error",
                "assert failed",
                "panic_print_str",
                "LoadProhibited",
                "StoreProhibited",
                "IllegalInstruction",
                "abort()",
                "stack overflow",
            ]

            for pattern in failure_patterns:
                if pattern.lower() in output.lower():
                    passed = False
                    errors.append(f"Crash detected: {pattern}")

            # Check for any serial output (sign of life)
            if not output.strip():
                passed = False
                errors.append("No serial output — firmware may be stuck")

            return {"output": output, "passed": passed, "errors": errors}

        except FileNotFoundError:
            return {
                "output": "",
                "passed": False,
                "errors": ["wokwi-cli not found. Install: npm i -g @wokwi/wokwi-cli"],
            }
        except asyncio.TimeoutError:
            return {
                "output": "Simulation timed out",
                "passed": False,
                "errors": [f"Timed out after {timeout}s"],
            }
        except Exception as e:
            return {
                "output": "",
                "passed": False,
                "errors": [f"Simulation error: {e}"],
            }
