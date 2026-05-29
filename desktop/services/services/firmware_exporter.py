"""
Firmware Export Service — Generate downloadable PlatformIO project ZIPs.

Creates a complete, ready-to-build PlatformIO project from:
  - Selected golden blocks
  - Target board
  - Auto-detected libraries
"""
import os
import io
import zipfile
from typing import Optional


class FirmwareExporter:
    """Exports firmware as a ready-to-build PlatformIO project ZIP."""

    def export_project(
        self,
        project_name: str,
        main_cpp: str,
        board_id: str = "esp32dev",
        lib_deps: Optional[list[str]] = None,
        extra_files: Optional[dict[str, str]] = None,
    ) -> bytes:
        """Generate a ZIP containing a full PlatformIO project."""
        from services.board_profiles import generate_platformio_ini

        buf = io.BytesIO()
        with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as zf:
            prefix = project_name.replace(" ", "_")

            # platformio.ini
            ini = generate_platformio_ini(board_id, lib_deps)
            zf.writestr(f"{prefix}/platformio.ini", ini)

            # src/main.cpp
            zf.writestr(f"{prefix}/src/main.cpp", main_cpp)

            # include/README
            zf.writestr(f"{prefix}/include/README", _INCLUDE_README)

            # lib/README
            zf.writestr(f"{prefix}/lib/README", _LIB_README)

            # .gitignore
            zf.writestr(f"{prefix}/.gitignore", _GITIGNORE)

            # Extra files (e.g. header files, config)
            if extra_files:
                for path, content in extra_files.items():
                    zf.writestr(f"{prefix}/{path}", content)

        return buf.getvalue()

    def export_firmware_binary(self, firmware_path: str) -> Optional[bytes]:
        """Read compiled firmware binary for OTA/flash."""
        if os.path.exists(firmware_path):
            with open(firmware_path, "rb") as f:
                return f.read()
        return None


_INCLUDE_README = """
This directory is intended for project header files.

A header file is a file containing C declarations and macro definitions
to be shared between several project source files using the `#include`
preprocessor directive.
""".strip()

_LIB_README = """
This directory is intended for project specific (private) libraries.
PlatformIO Library Dependency Finder will pick them up automatically.
""".strip()

_GITIGNORE = """.pio
.vscode/.browse.c_cpp.db*
.vscode/c_cpp_properties.json
.vscode/launch.json
.vscode/ipch
"""
