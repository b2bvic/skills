#!/usr/bin/env python3
"""Install skill folders without replacing existing entries."""
import argparse
from pathlib import Path
import shutil


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--dest", type=Path, default=Path.home() / ".claude/skills")
    args = parser.parse_args()
    source = Path(__file__).resolve().parent / "skills"
    folders = sorted(p.parent for p in source.glob("*/SKILL.md"))
    destination = args.dest.expanduser().resolve()
    conflicts = [destination / p.name for p in folders
                 if (destination / p.name).exists() or (destination / p.name).is_symlink()]
    if conflicts:
        parser.exit(2, "No skills installed. Existing paths: " + ", ".join(map(str, conflicts)) + "\n")
    destination.mkdir(parents=True, exist_ok=True)
    for folder in folders:
        shutil.copytree(folder, destination / folder.name)
        print(destination / folder.name)


if __name__ == "__main__":
    main()
