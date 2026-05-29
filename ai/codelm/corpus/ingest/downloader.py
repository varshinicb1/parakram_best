"""Git clone + tarball fetch for upstream sources."""

import subprocess
from pathlib import Path

from config import RAW_DIR
from corpus.ingest.sources import ALL_SOURCES, SourceRepo


def clone_repo(source: SourceRepo, target_dir: Path) -> bool:
    """Clone a single source repo. Returns True on success."""
    dest = target_dir / source.name
    if dest.exists():
        print(f"  [skip] {source.name} already exists")
        return True

    cmd = ["git", "clone"]
    if source.shallow:
        cmd.extend(["--depth", "1"])
    cmd.extend(["--branch", source.ref, source.url, str(dest)])

    try:
        subprocess.run(cmd, check=True, capture_output=True, timeout=600)
        print(f"  [ok] {source.name} cloned ({source.ref})")
        return True
    except subprocess.CalledProcessError as e:
        print(f"  [fail] {source.name}: {e.stderr.decode()[:200]}")
        return False
    except subprocess.TimeoutExpired:
        print(f"  [timeout] {source.name}")
        return False


def download_all_sources(sources_file: Path | None = None) -> dict[str, int]:
    """Download all upstream sources into RAW_DIR."""
    RAW_DIR.mkdir(parents=True, exist_ok=True)

    success = 0
    failed = 0
    skipped = 0

    for source in ALL_SOURCES:
        dest = RAW_DIR / source.name
        if dest.exists():
            skipped += 1
            continue
        if clone_repo(source, RAW_DIR):
            success += 1
        else:
            failed += 1

    return {"success": success, "failed": failed, "skipped": skipped}
