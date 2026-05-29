"""
Runtime Library Fetcher — Query PlatformIO registry for any library on demand.

Searches the PlatformIO library registry API,
downloads headers, and parses them for API signatures.
Eliminates the need for pre-curing every possible library.
"""

import os
import re
import json
import aiohttp
from typing import Optional

PIO_REGISTRY = "https://api.registry.platformio.org/v3"


async def search_pio_registry(query: str, limit: int = 5) -> list[dict]:
    """
    Search PlatformIO library registry.

    Returns list of:
    {
        "name": str,
        "description": str,
        "owner": str,
        "version": str,
        "lib_dep": str,  # for platformio.ini
        "headers": [str],
        "frameworks": [str],
        "platforms": [str],
        "download_url": str,
    }
    """
    results = []
    try:
        async with aiohttp.ClientSession() as session:
            url = f"{PIO_REGISTRY}/search"
            params = {"query": query, "limit": limit}
            async with session.get(url, params=params, timeout=aiohttp.ClientTimeout(total=10)) as resp:
                if resp.status != 200:
                    return results
                data = await resp.json()

                for item in data.get("items", []):
                    name = item.get("name", "")
                    owner = item.get("owner", {}).get("username", "")
                    version = item.get("version", {}).get("name", "")

                    # Extract headers from manifest
                    headers = item.get("version", {}).get("headers", [])
                    if not headers:
                        headers = [f"{name}.h"]

                    results.append({
                        "name": name,
                        "description": item.get("description", "")[:200],
                        "owner": owner,
                        "version": version,
                        "lib_dep": f"{owner}/{name}@^{version}" if owner else name,
                        "headers": headers,
                        "frameworks": item.get("frameworks", []),
                        "platforms": item.get("platforms", []),
                    })
    except Exception as e:
        print(f"[lib_fetch] Registry search failed: {e}")

    return results


async def fetch_and_parse(lib_dep: str) -> Optional[dict]:
    """
    Install a library via PlatformIO and parse its headers.
    Returns parsed API info.
    """
    import subprocess
    from agents.header_parser import scan_library_dir

    # Install to a temp location
    try:
        proc = subprocess.run(
            ["pio", "pkg", "install", "-g", "-l", lib_dep],
            capture_output=True, text=True, timeout=60,
        )
        if proc.returncode != 0:
            return None

        # Find installed location
        global_lib = os.path.expanduser("~/.platformio/lib")
        lib_name = lib_dep.split("/")[-1].split("@")[0]

        for d in os.listdir(global_lib):
            if lib_name.lower() in d.lower():
                lib_path = os.path.join(global_lib, d)
                parsed = scan_library_dir(lib_path)
                return parsed

    except Exception as e:
        print(f"[lib_fetch] Install failed: {e}")

    return None


def get_lib_dep_string(name: str, owner: str = "", version: str = "") -> str:
    """Build a PlatformIO lib_deps string."""
    if owner:
        dep = f"{owner}/{name}"
    else:
        dep = name
    if version:
        dep += f"@^{version}"
    return dep
