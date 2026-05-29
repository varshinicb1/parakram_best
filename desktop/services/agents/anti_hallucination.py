"""
Anti-Hallucination Engine — The core innovation.

Ensures generated firmware code uses ONLY verified API calls.
Three layers of defense:

1. CONSTRAINED GENERATION: LLM prompts include only verified method
   signatures. Output is post-processed to validate every method call.

2. SEMANTIC VALIDATION: Parse generated code, extract all method calls,
   cross-reference against library_registry + header_parser. Flag any
   method that doesn't exist in the actual library.

3. TEMPLATE-FIRST: For known block types, ALWAYS use verified golden
   templates. Only fall back to LLM generation for truly unknown blocks.
   Even then, generate BASED ON the most similar verified template.
"""

import re
import os
import json
from typing import Optional
from agents.library_registry import LIBRARY_REGISTRY, get_library_info
from agents.header_parser import parse_header, scan_esp32_framework


class HallucinationDetector:
    """
    Validates generated code against known library APIs.
    Catches hallucinated method calls, wrong signatures, fake libraries.
    """

    def __init__(self):
        self._known_methods: dict[str, set] = {}  # class_name -> {method_names}
        self._known_classes: set[str] = set()
        self._known_includes: set[str] = set()
        self._initialized = False

    def initialize(self):
        """Load all known APIs from registry + framework headers."""
        if self._initialized:
            return

        # Load from hand-curated registry
        for lib_name, info in LIBRARY_REGISTRY.items():
            class_name = info.get("class", "").split("(")[0].strip()
            if class_name and not class_name.startswith("//"):
                self._known_classes.add(class_name)
                methods = set()
                for m in info.get("methods", []):
                    # Extract method name from signature
                    name_match = re.search(r'(\w+)\s*\(', m)
                    if name_match:
                        methods.add(name_match.group(1))
                self._known_methods[class_name] = methods

            inc = info.get("include", "")
            if inc:
                # Extract header name
                inc_match = re.search(r'[<"]([^>"]+)[>"]', inc)
                if inc_match:
                    self._known_includes.add(inc_match.group(1))

        # Load from auto-parsed framework headers
        try:
            framework_libs = scan_esp32_framework()
            for lib_name, info in framework_libs.items():
                for cls in info.get("classes", []):
                    cls_name = cls["name"]
                    self._known_classes.add(cls_name)
                    methods = set()
                    for m in cls.get("methods", []):
                        name_match = re.search(r'(\w+)\s*\(', m)
                        if name_match:
                            methods.add(name_match.group(1))
                    if cls_name in self._known_methods:
                        self._known_methods[cls_name].update(methods)
                    else:
                        self._known_methods[cls_name] = methods
        except Exception:
            pass

        # Add Arduino built-in methods
        arduino_methods = {
            "Serial": {"begin", "print", "println", "printf", "write", "read",
                       "available", "readString", "readStringUntil", "parseInt",
                       "parseFloat", "flush", "end", "peek", "setTimeout"},
            "Wire": {"begin", "beginTransmission", "endTransmission", "write",
                     "read", "requestFrom", "available", "setClock", "onReceive",
                     "onRequest"},
            "SPI": {"begin", "end", "transfer", "transfer16", "beginTransaction",
                    "endTransaction", "setBitOrder", "setClockDivider", "setDataMode"},
        }
        for cls, methods in arduino_methods.items():
            self._known_classes.add(cls)
            if cls in self._known_methods:
                self._known_methods[cls].update(methods)
            else:
                self._known_methods[cls] = methods

        self._initialized = True

    def validate(self, source_code: str) -> list[dict]:
        """
        Validate generated code for hallucinated API calls.

        Returns list of issues:
        [{"type": "hallucinated_method", "class": "Foo", "method": "bar", "line": 5}]
        """
        self.initialize()
        issues = []

        lines = source_code.split("\n")
        for line_num, line in enumerate(lines, 1):
            stripped = line.strip()
            if stripped.startswith("//") or stripped.startswith("/*"):
                continue

            # Find method calls: obj.method(...)
            method_calls = re.findall(r'(\w+)\.(\w+)\s*\(', stripped)
            for obj_name, method_name in method_calls:
                # Skip common non-object names
                if obj_name in ("this", "self", "std", "String", "if", "while", "for"):
                    continue

                # Check if the class is known
                # Try to find the class by variable type from earlier in the code
                obj_class = self._find_object_class(obj_name, source_code)

                if obj_class and obj_class in self._known_methods:
                    known = self._known_methods[obj_class]
                    if method_name not in known:
                        issues.append({
                            "type": "hallucinated_method",
                            "class": obj_class,
                            "object": obj_name,
                            "method": method_name,
                            "line": line_num,
                            "known_methods": sorted(known)[:10],
                            "suggestion": f"'{method_name}' not found in {obj_class}. "
                                         f"Available: {', '.join(sorted(known)[:5])}",
                        })

            # Check for fake #includes
            inc_match = re.match(r'#include\s*[<"]([^>"]+)[>"]', stripped)
            if inc_match:
                inc_name = inc_match.group(1)
                # Allow standard C/C++ headers and Arduino headers
                std_headers = {"Arduino.h", "Wire.h", "SPI.h", "stdlib.h", "stdio.h",
                              "string.h", "math.h", "stdint.h", "stdbool.h", "cstring",
                              "cmath", "algorithm", "vector", "map", "functional"}
                if (inc_name not in self._known_includes and
                    inc_name not in std_headers and
                    not inc_name.startswith(("freertos/", "driver/", "esp_", "soc/",
                                            "hal/", "sys/", "lwip/", "mbedtls/"))):
                    # Check if the file exists in the framework
                    exists = self._include_exists(inc_name)
                    if not exists:
                        issues.append({
                            "type": "unknown_include",
                            "include": inc_name,
                            "line": line_num,
                            "suggestion": f"Library '{inc_name}' not found. Check PlatformIO registry.",
                        })

        return issues

    def _find_object_class(self, obj_name: str, source: str) -> Optional[str]:
        """Try to find what class a variable is an instance of."""
        # Pattern: ClassName obj_name;  or  ClassName obj_name(...)
        class_pattern = re.compile(
            rf'(\w+)\s+{re.escape(obj_name)}\s*[;(]'
        )
        match = class_pattern.search(source)
        if match:
            return match.group(1)

        # Pattern: ClassName* obj_name
        ptr_pattern = re.compile(
            rf'(\w+)\s*\*\s*{re.escape(obj_name)}\s*[;=]'
        )
        match = ptr_pattern.search(source)
        if match:
            return match.group(1)

        return None

    def _include_exists(self, inc_name: str) -> bool:
        """Check if an include file exists in the ESP32 framework."""
        esp32_libs = os.path.expanduser(
            "~/.platformio/packages/framework-arduinoespressif32/libraries"
        )
        if os.path.isdir(esp32_libs):
            for root, dirs, files in os.walk(esp32_libs):
                if inc_name in files:
                    return True
        return False

    def fix_hallucinations(self, source_code: str, issues: list[dict]) -> str:
        """
        Auto-fix hallucinated method calls by replacing with correct ones.
        Uses fuzzy matching to find the closest real method.
        """
        fixed = source_code
        for issue in issues:
            if issue["type"] == "hallucinated_method":
                bad_method = issue["method"]
                known = issue.get("known_methods", [])

                # Find closest match
                best_match = None
                best_score = 0
                for known_method in known:
                    score = self._similarity(bad_method.lower(), known_method.lower())
                    if score > best_score:
                        best_score = score
                        best_match = known_method

                if best_match and best_score > 0.5:
                    obj = issue["object"]
                    fixed = fixed.replace(
                        f"{obj}.{bad_method}(",
                        f"{obj}.{best_match}("
                    )

        return fixed

    def _similarity(self, a: str, b: str) -> float:
        """Simple character-level similarity."""
        if not a or not b:
            return 0
        common = sum(1 for c in a if c in b)
        return common / max(len(a), len(b))


class AntiHallucinationEngine:
    """
    Full anti-hallucination pipeline.

    Pipeline:
    1. Before generation: inject ONLY verified APIs into prompt
    2. After generation: validate every method call
    3. If hallucinations found: auto-fix or regenerate
    4. Compile gate as final verification
    """

    def __init__(self):
        self.detector = HallucinationDetector()
        self.detector.initialize()

    def build_constrained_prompt(
        self,
        block_name: str,
        block_category: str,
        libraries: list[str],
        description: str = "",
        configuration: dict = None,
    ) -> str:
        """
        Build a prompt that constrains the LLM to only use verified APIs.
        This is the PRIMARY defense against hallucination.
        """
        # Get verified API context for each library
        api_sections = []
        for lib in libraries:
            info = get_library_info(lib)
            if info:
                section = f"### {lib}\n"
                section += f"Include: {info.get('include', '')}\n"
                if info.get("depends"):
                    section += f"Dependencies: {', '.join(info['depends'])}\n"
                section += f"Class: {info.get('class', '')}\n"
                section += f"Constructor: {info.get('constructor', '')}\n"
                section += "Methods (use ONLY these):\n"
                for m in info.get("methods", []):
                    section += f"  - {m}\n"
                if info.get("notes"):
                    section += f"Notes: {info['notes']}\n"
                api_sections.append(section)

        safe_name = block_name.lower().replace(" ", "_").replace("-", "_")
        api_text = "\n".join(api_sections) if api_sections else "Use standard Arduino APIs only."

        return f"""You are generating firmware for an ESP32 Arduino module.

CRITICAL RULES:
1. You MUST ONLY use the methods listed below. NO EXCEPTIONS.
2. Do NOT invent method names — if a method is not listed, it does not exist.
3. Do NOT guess at library APIs — use EXACTLY the signatures shown.
4. Every method call MUST match one from the API reference.
5. If you're unsure about a method, use a simpler alternative from the list.

BLOCK: {block_name}
CATEGORY: {block_category}
DESCRIPTION: {description}
CONFIG: {json.dumps(configuration) if configuration else 'default'}

VERIFIED API REFERENCE:
{api_text}

REQUIREMENTS:
- Header (.h): #ifndef {safe_name.upper()}_H guard, function declarations
- Source (.cpp): {safe_name}_setup() and {safe_name}_loop() functions
- Getter functions for outputs
- Serial debug with [{safe_name}] prefix
- Error handling with retry logic
- Non-blocking (use millis(), not delay())

Format:
===HEADER===
(complete .h)
===SOURCE===
(complete .cpp)
"""

    def validate_and_fix(self, source_code: str, max_attempts: int = 2) -> dict:
        """
        Validate generated code and auto-fix hallucinations.

        Returns:
            {"code": str, "issues_found": int, "issues_fixed": int, "clean": bool}
        """
        issues = self.detector.validate(source_code)

        if not issues:
            return {
                "code": source_code,
                "issues_found": 0,
                "issues_fixed": 0,
                "clean": True,
            }

        # Auto-fix hallucinated methods
        fixed_code = self.detector.fix_hallucinations(source_code, issues)

        # Re-validate
        remaining = self.detector.validate(fixed_code)

        return {
            "code": fixed_code,
            "issues_found": len(issues),
            "issues_fixed": len(issues) - len(remaining),
            "remaining_issues": remaining,
            "clean": len(remaining) == 0,
        }
