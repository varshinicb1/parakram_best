"""
Parakram Sidecar Build Script — packages the Python backend as a standalone
executable using PyInstaller, then copies it to the Tauri sidecar directory.

Usage:
    python build_sidecar.py          # Build for current platform
    python build_sidecar.py --clean  # Clean previous builds first
"""
import os
import sys
import shutil
import platform
import subprocess

ROOT = os.path.dirname(os.path.abspath(__file__))
BACKEND = os.path.join(ROOT, "backend")
DESKTOP = os.path.join(ROOT, "desktop")
SIDECAR_DIR = os.path.join(DESKTOP, "src-tauri", "binaries")

# Platform-specific binary naming for Tauri sidecar convention
PLATFORM_MAP = {
    ("Windows", "AMD64"): "x86_64-pc-windows-msvc",
    ("Windows", "x86"):   "i686-pc-windows-msvc",
    ("Linux", "x86_64"):  "x86_64-unknown-linux-gnu",
    ("Linux", "aarch64"): "aarch64-unknown-linux-gnu",
    ("Darwin", "x86_64"): "x86_64-apple-darwin",
    ("Darwin", "arm64"):  "aarch64-apple-darwin",
}


def get_target_triple():
    """Get the Rust-style target triple for the current platform."""
    system = platform.system()
    machine = platform.machine()
    return PLATFORM_MAP.get((system, machine), f"{machine}-unknown-{system.lower()}")


def clean():
    """Remove previous build artifacts."""
    for d in ["build", "dist", "__pycache__"]:
        path = os.path.join(BACKEND, d)
        if os.path.exists(path):
            shutil.rmtree(path)
            print(f"  Cleaned {d}/")
    spec = os.path.join(BACKEND, "main.spec")
    if os.path.exists(spec):
        os.remove(spec)


def build():
    """Build sidecar binary with PyInstaller."""
    triple = get_target_triple()
    ext = ".exe" if platform.system() == "Windows" else ""
    binary_name = f"parakram-backend-{triple}{ext}"

    print(f"\n{'='*60}")
    print(f"  PARAKRAM SIDECAR BUILD")
    print(f"  Target: {triple}")
    print(f"  Output: {binary_name}")
    print(f"{'='*60}\n")

    # Step 1: Install PyInstaller if not present
    try:
        import PyInstaller  # noqa: F401
    except ImportError:
        print("Installing PyInstaller...")
        subprocess.check_call([sys.executable, "-m", "pip", "install", "pyinstaller"])

    # Step 2: Build with PyInstaller
    cmd = [
        sys.executable, "-m", "PyInstaller",
        "--onefile",
        "--name", f"parakram-backend-{triple}",
        "--distpath", os.path.join(BACKEND, "dist"),
        "--workpath", os.path.join(BACKEND, "build"),
        "--specpath", BACKEND,
        "--hidden-import", "uvicorn",
        "--hidden-import", "uvicorn.logging",
        "--hidden-import", "uvicorn.loops",
        "--hidden-import", "uvicorn.loops.auto",
        "--hidden-import", "uvicorn.protocols",
        "--hidden-import", "uvicorn.protocols.http",
        "--hidden-import", "uvicorn.protocols.http.auto",
        "--hidden-import", "uvicorn.protocols.websockets",
        "--hidden-import", "uvicorn.protocols.websockets.auto",
        "--hidden-import", "uvicorn.lifespan",
        "--hidden-import", "uvicorn.lifespan.on",
        "--hidden-import", "fastapi",
        "--hidden-import", "pydantic",
        "--hidden-import", "numpy",
        "--collect-all", "agents",
        "--collect-all", "services",
        "--collect-all", "api",
        os.path.join(BACKEND, "main.py"),
    ]

    print("Building sidecar binary...")
    subprocess.check_call(cmd)

    # Step 3: Copy to Tauri sidecar directory
    os.makedirs(SIDECAR_DIR, exist_ok=True)
    src = os.path.join(BACKEND, "dist", binary_name)
    dst = os.path.join(SIDECAR_DIR, binary_name)

    if os.path.exists(src):
        shutil.copy2(src, dst)
        size_mb = os.path.getsize(dst) / (1024 * 1024)
        print(f"\n✓ Sidecar binary: {dst}")
        print(f"  Size: {size_mb:.1f} MB")
    else:
        print(f"\n✗ Build failed: {src} not found")
        sys.exit(1)

    print(f"\n{'='*60}")
    print(f"  BUILD COMPLETE")
    print(f"  Next: cd desktop && cargo tauri build")
    print(f"{'='*60}\n")


if __name__ == "__main__":
    if "--clean" in sys.argv:
        print("Cleaning previous builds...")
        clean()
    build()
