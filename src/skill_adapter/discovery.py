from pathlib import Path
from typing import List


def discover_skill_dirs(skill_dirs: List[str]) -> List[Path]:
    discovered: List[Path] = []
    for base_dir in skill_dirs:
        root = Path(base_dir)
        if not root.exists() or not root.is_dir():
            continue
        for child in root.iterdir():
            if child.is_dir() and (child / "SKILL.md").is_file():
                discovered.append(child)
    return discovered


def discover_skill_files(skill_dirs: List[str]) -> List[Path]:
    """
    Discover markdown skill definitions in this format:
    skills/<sub_dir>/<any_name>.md
    """
    files: List[Path] = []
    for base_dir in skill_dirs:
        root = Path(base_dir)
        if not root.exists() or not root.is_dir():
            continue

        for child in root.iterdir():
            if not child.is_dir():
                continue
            for md in child.rglob("*.md"):
                if md.is_file():
                    files.append(md)

    # Deduplicate while preserving order.
    unique: List[Path] = []
    seen: set[str] = set()
    for f in files:
        key = str(f.resolve())
        if key in seen:
            continue
        seen.add(key)
        unique.append(f)
    return unique
