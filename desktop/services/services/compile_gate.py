"""
Compile Gate — Isolated per-block compilation testing.

Before assembling the full project, tests each block's firmware
in isolation to catch errors early. Blocks that fail get auto-fixed
via self-healing. Maintains a compile scoreboard.
"""

import os
import json
import asyncio
import tempfile
import shutil
from datetime import datetime
from typing import Optional

from services.self_healing_compiler import SelfHealingCompiler
from services.lib_resolver import scan_includes, resolve_lib_deps


PROJECTS_DIR = os.environ.get("PROJECTS_DIR", "../projects")
SCOREBOARD_FILE = os.path.join(os.path.dirname(__file__), "..", ".cache", "compile_scoreboard.json")


class CompileGate:
    """
    Tests each block's firmware code in isolation before assembly.

    Creates a temporary PlatformIO project per block, compiles it,
    and feeds failures into the self-healing loop.
    """

    def __init__(self, board: str = "esp32dev"):
        self.board = board
        self.healer = SelfHealingCompiler(max_retries=2)
        self._scoreboard = self._load_scoreboard()

    def _load_scoreboard(self) -> dict:
        """Load compile success/failure history."""
        try:
            if os.path.exists(SCOREBOARD_FILE):
                with open(SCOREBOARD_FILE, "r") as f:
                    return json.load(f)
        except Exception:
            pass
        return {}

    def _save_scoreboard(self):
        """Persist scoreboard to disk."""
        try:
            os.makedirs(os.path.dirname(SCOREBOARD_FILE), exist_ok=True)
            with open(SCOREBOARD_FILE, "w") as f:
                json.dump(self._scoreboard, f, indent=2)
        except Exception:
            pass

    async def test_block(
        self,
        block_id: str,
        header: str,
        source: str,
        libraries: list[str] = None,
    ) -> dict:
        """
        Compile-test a single block in isolation.

        Creates a temp PlatformIO project with the block's code,
        adds a minimal main.cpp that calls setup/loop, compiles.

        Returns:
            {"passed": bool, "errors": [...], "fixed_code": {...}, "attempts": int}
        """
        safe_name = block_id.lower().replace(" ", "_").replace("-", "_")

        # Create temp project
        tmpdir = tempfile.mkdtemp(prefix=f"parakram_gate_{safe_name}_")

        try:
            # Project structure
            src_dir = os.path.join(tmpdir, "firmware", "src")
            inc_dir = os.path.join(tmpdir, "firmware", "include")
            os.makedirs(src_dir, exist_ok=True)
            os.makedirs(inc_dir, exist_ok=True)

            # Write block header
            if header:
                with open(os.path.join(inc_dir, f"{safe_name}.h"), "w", encoding="utf-8") as f:
                    f.write(header)

            # Write block source
            with open(os.path.join(src_dir, f"{safe_name}.cpp"), "w", encoding="utf-8") as f:
                f.write(source)

            # Write minimal main.cpp that calls the block
            main_cpp = f"""#include <Arduino.h>
#include "{safe_name}.h"

void setup() {{
    Serial.begin(115200);
    {safe_name}_setup();
}}

void loop() {{
    {safe_name}_loop();
    delay(100);
}}
"""
            with open(os.path.join(src_dir, "main.cpp"), "w", encoding="utf-8") as f:
                f.write(main_cpp)

            # Resolve library dependencies
            all_source_files = [
                os.path.join(src_dir, f"{safe_name}.cpp"),
                os.path.join(inc_dir, f"{safe_name}.h"),
            ]
            includes = scan_includes(all_source_files)
            lib_deps = resolve_lib_deps(includes)

            # Write platformio.ini
            deps_str = "\n    ".join(lib_deps) if lib_deps else ""
            ini_content = f"""[env:{self.board}]
platform = espressif32
board = {self.board}
framework = arduino
monitor_speed = 115200
"""
            if deps_str:
                ini_content += f"\nlib_deps =\n    {deps_str}\n"

            with open(os.path.join(tmpdir, "firmware", "platformio.ini"), "w") as f:
                f.write(ini_content)

            # Compile with self-healing
            compile_result = await self.healer.compile_with_healing(
                project_dir=tmpdir,
                board=self.board,
            )

            passed = compile_result.get("status") == "success"
            attempts = compile_result.get("attempts", 0)
            errors = []

            if not passed:
                for attempt in compile_result.get("history", []):
                    for err in attempt.get("errors", []):
                        errors.append(str(err))

            # If healed, grab the fixed code
            fixed_code = {}
            if attempts > 1 and passed:
                # Read back the fixed files
                fixed_src = os.path.join(src_dir, f"{safe_name}.cpp")
                fixed_hdr = os.path.join(inc_dir, f"{safe_name}.h")
                if os.path.exists(fixed_src):
                    with open(fixed_src, "r") as f:
                        fixed_code["source"] = f.read()
                if os.path.exists(fixed_hdr):
                    with open(fixed_hdr, "r") as f:
                        fixed_code["header"] = f.read()

            # Update scoreboard
            self._scoreboard[block_id] = {
                "passed": passed,
                "attempts": attempts,
                "errors": errors[:5],
                "lib_deps": lib_deps,
                "last_tested": datetime.now().isoformat(),
                "self_healed": attempts > 1 and passed,
            }
            self._save_scoreboard()

            return {
                "passed": passed,
                "attempts": attempts,
                "errors": errors,
                "fixed_code": fixed_code,
                "lib_deps": lib_deps,
            }

        finally:
            # Cleanup temp project
            try:
                shutil.rmtree(tmpdir, ignore_errors=True)
            except Exception:
                pass

    async def test_all_blocks(self, blocks: list[dict]) -> dict:
        """
        Compile-test all blocks sequentially.

        Args:
            blocks: List of {"id": str, "header": str, "source": str, "libraries": [...]}

        Returns:
            {"total": N, "passed": N, "failed": N, "healed": N, "results": [...]}
        """
        results = []
        passed = 0
        failed_count = 0
        healed = 0

        for block in blocks:
            block_id = block.get("id", "unknown")
            header = block.get("header", "")
            source = block.get("source", "")
            libs = block.get("libraries", [])

            if not source or len(source) < 20:
                results.append({"id": block_id, "skipped": True, "reason": "no source"})
                continue

            print(f"[Gate] Testing {block_id}...", end=" ", flush=True)
            result = await self.test_block(block_id, header, source, libs)

            if result["passed"]:
                passed += 1
                if result["attempts"] > 1:
                    healed += 1
                    print(f"HEALED (attempt {result['attempts']})")
                else:
                    print("OK")
            else:
                failed_count += 1
                print(f"FAILED ({len(result['errors'])} errors)")

            results.append({"id": block_id, **result})

        total = passed + failed_count
        return {
            "total": total,
            "passed": passed,
            "failed": failed_count,
            "healed": healed,
            "pass_rate": f"{passed/total*100:.0f}%" if total else "N/A",
            "results": results,
        }

    def get_scoreboard(self) -> dict:
        """Get the compile scoreboard with per-block history."""
        return {
            "blocks": self._scoreboard,
            "summary": {
                "total": len(self._scoreboard),
                "passed": sum(1 for b in self._scoreboard.values() if b.get("passed")),
                "failed": sum(1 for b in self._scoreboard.values() if not b.get("passed")),
                "healed": sum(1 for b in self._scoreboard.values() if b.get("self_healed")),
            },
        }
