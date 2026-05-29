"""
Header Parser — Auto-extracts class names, method signatures, enums, and
constants from C/C++ header files.

Scans PlatformIO framework libraries and installed project libs to build
a comprehensive API knowledge base at runtime.
"""

import os
import re
import json
from typing import Optional
from pathlib import Path


# PlatformIO paths
PIO_HOME = os.path.expanduser("~/.platformio")
ESP32_FRAMEWORK = os.path.join(PIO_HOME, "packages", "framework-arduinoespressif32")
ESP32_LIBS = os.path.join(ESP32_FRAMEWORK, "libraries")
ESP32_CORES = os.path.join(ESP32_FRAMEWORK, "cores", "esp32")

# Cache parsed headers
_header_cache: dict[str, dict] = {}


def parse_header(filepath: str) -> dict:
    """
    Parse a C/C++ header file and extract:
    - Class names and their public methods
    - Standalone function declarations
    - Enum definitions
    - #define constants
    """
    if filepath in _header_cache:
        return _header_cache[filepath]

    try:
        with open(filepath, "r", encoding="utf-8", errors="replace") as f:
            content = f.read()
    except Exception:
        return {}

    result = {
        "file": filepath,
        "classes": [],
        "functions": [],
        "enums": [],
        "defines": [],
    }

    # Remove comments
    content_no_comments = re.sub(r'//.*$', '', content, flags=re.MULTILINE)
    content_no_comments = re.sub(r'/\*.*?\*/', '', content_no_comments, flags=re.DOTALL)

    # ── Extract classes ──────────────────────────────────
    class_pattern = re.compile(
        r'class\s+(\w+)\s*(?::\s*(?:public|private|protected)\s+\w+)?\s*\{',
        re.MULTILINE
    )
    for match in class_pattern.finditer(content_no_comments):
        class_name = match.group(1)
        # Find the class body
        start = match.end()
        brace_count = 1
        pos = start
        while pos < len(content_no_comments) and brace_count > 0:
            if content_no_comments[pos] == '{':
                brace_count += 1
            elif content_no_comments[pos] == '}':
                brace_count -= 1
            pos += 1

        class_body = content_no_comments[start:pos - 1]

        # Extract public methods
        methods = _extract_methods(class_body)

        result["classes"].append({
            "name": class_name,
            "methods": methods,
        })

    # ── Extract standalone functions ─────────────────────
    func_pattern = re.compile(
        r'^(?:extern\s+)?(?:static\s+)?(?:inline\s+)?'
        r'([\w:*&<>,\s]+?)\s+(\w+)\s*\(([^)]*)\)\s*;',
        re.MULTILINE
    )
    for match in func_pattern.finditer(content_no_comments):
        ret_type = match.group(1).strip()
        func_name = match.group(2).strip()
        params = match.group(3).strip()
        # Skip constructors, destructors, and common non-functions
        if func_name.startswith('_') or ret_type in ('class', 'struct', 'typedef', 'enum'):
            continue
        result["functions"].append(f"{ret_type} {func_name}({params})")

    # ── Extract enums ────────────────────────────────────
    enum_pattern = re.compile(
        r'(?:typedef\s+)?enum\s*(?:class\s+)?(\w+)?\s*\{([^}]+)\}',
        re.DOTALL
    )
    for match in enum_pattern.finditer(content_no_comments):
        enum_name = match.group(1) or "anonymous"
        values = [v.strip().split('=')[0].strip().split('/')[0].strip()
                  for v in match.group(2).split(',')
                  if v.strip() and not v.strip().startswith('//')]
        values = [v for v in values if v and v.isidentifier()]
        if values:
            result["enums"].append({"name": enum_name, "values": values[:20]})

    # ── Extract important #defines ───────────────────────
    define_pattern = re.compile(r'#define\s+(\w+)\s+(.+?)$', re.MULTILINE)
    for match in define_pattern.finditer(content_no_comments):
        name = match.group(1)
        value = match.group(2).strip()
        # Skip include guards and internal macros
        if name.endswith('_H') or name.endswith('_H_') or name.startswith('_'):
            continue
        if len(value) < 50:  # Skip long macro bodies
            result["defines"].append(f"{name} = {value}")

    _header_cache[filepath] = result
    return result


def _extract_methods(class_body: str) -> list[str]:
    """Extract public method signatures from a class body."""
    methods = []

    # Find the public section
    public_start = class_body.find("public:")
    if public_start == -1:
        # Treat entire body as public (struct-like)
        section = class_body
    else:
        # Find next access modifier or end
        next_private = class_body.find("private:", public_start + 7)
        next_protected = class_body.find("protected:", public_start + 7)

        end = len(class_body)
        if next_private != -1:
            end = min(end, next_private)
        if next_protected != -1:
            end = min(end, next_protected)

        section = class_body[public_start + 7:end]

    # Match method declarations
    method_pattern = re.compile(
        r'(?:virtual\s+)?(?:static\s+)?(?:inline\s+)?'
        r'([\w:*&<>,\s]+?)\s+(\w+)\s*\(([^)]*)\)\s*'
        r'(?:const\s*)?(?:override\s*)?(?:=\s*0\s*)?;',
        re.MULTILINE
    )

    for match in method_pattern.finditer(section):
        ret_type = match.group(1).strip()
        name = match.group(2).strip()
        params = match.group(3).strip()

        # Skip destructors and operators
        if name.startswith('~') or name.startswith('operator'):
            continue

        # Clean up params
        params = re.sub(r'\s+', ' ', params)
        methods.append(f"{ret_type} {name}({params})")

    # Match constructors
    # Constructors don't have a return type
    ctor_pattern = re.compile(
        r'(\w+)\s*\(([^)]*)\)\s*;', re.MULTILINE
    )
    for match in ctor_pattern.finditer(section):
        name = match.group(1).strip()
        params = match.group(2).strip()
        if name and name[0].isupper() and not any(
            c in name for c in ['=', '+', '-', '*', '/', '<', '>']
        ):
            methods.insert(0, f"{name}({params})")

    return methods[:30]  # Cap at 30 methods


def scan_library_dir(lib_dir: str) -> dict[str, dict]:
    """Scan a library directory and parse all headers."""
    results = {}

    if not os.path.isdir(lib_dir):
        return results

    for lib_name in sorted(os.listdir(lib_dir)):
        lib_path = os.path.join(lib_dir, lib_name)
        if not os.path.isdir(lib_path):
            continue

        # Find header files (in src/, root, or src/ subdirs)
        headers = []
        for search_dir in [lib_path, os.path.join(lib_path, "src")]:
            if os.path.isdir(search_dir):
                for fname in os.listdir(search_dir):
                    if fname.endswith(".h") and not fname.startswith("_"):
                        headers.append(os.path.join(search_dir, fname))

        if not headers:
            continue

        # Parse each header
        all_classes = []
        all_functions = []
        all_enums = []
        main_include = None

        for hdr in headers[:5]:  # Limit to 5 headers per lib
            parsed = parse_header(hdr)
            all_classes.extend(parsed.get("classes", []))
            all_functions.extend(parsed.get("functions", []))
            all_enums.extend(parsed.get("enums", []))
            if main_include is None:
                main_include = f"#include <{os.path.basename(hdr)}>"

        if all_classes or all_functions:
            results[lib_name] = {
                "include": main_include,
                "classes": all_classes[:5],
                "functions": all_functions[:20],
                "enums": all_enums[:10],
            }

    return results


def scan_esp32_framework() -> dict[str, dict]:
    """Scan all ESP32 Arduino framework libraries."""
    return scan_library_dir(ESP32_LIBS)


def scan_project_libs(project_dir: str) -> dict[str, dict]:
    """Scan project-local .pio/libdeps for installed libraries."""
    libdeps_dir = os.path.join(project_dir, "firmware", ".pio", "libdeps")
    results = {}
    if os.path.isdir(libdeps_dir):
        for env_dir in os.listdir(libdeps_dir):
            env_path = os.path.join(libdeps_dir, env_dir)
            if os.path.isdir(env_path):
                results.update(scan_library_dir(env_path))
    return results


def get_api_for_includes(includes: list[str]) -> str:
    """
    Given a list of #include names, return full API context string
    by parsing the actual header files.
    """
    context_parts = []

    for inc in includes:
        inc_name = inc.strip().strip('<>"')
        # Search in ESP32 framework
        found = False
        for search_base in [ESP32_LIBS, ESP32_CORES]:
            if not os.path.isdir(search_base):
                continue
            for root, dirs, files in os.walk(search_base):
                if inc_name in files:
                    hdr_path = os.path.join(root, inc_name)
                    parsed = parse_header(hdr_path)
                    if parsed.get("classes") or parsed.get("functions"):
                        context_parts.append(_format_parsed(inc_name, parsed))
                        found = True
                        break
            if found:
                break

    return "\n\n".join(context_parts)


def _format_parsed(header_name: str, parsed: dict) -> str:
    """Format parsed header into prompt-ready context."""
    lines = [f"--- {header_name} (auto-parsed) ---"]

    for cls in parsed.get("classes", [])[:3]:
        lines.append(f"\nClass: {cls['name']}")
        lines.append("Methods:")
        for m in cls["methods"][:15]:
            lines.append(f"  - {m}")

    for func in parsed.get("functions", [])[:10]:
        lines.append(f"  - {func}")

    for enum in parsed.get("enums", [])[:5]:
        lines.append(f"\nEnum {enum['name']}: {', '.join(enum['values'][:10])}")

    return "\n".join(lines)
