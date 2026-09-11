#!/usr/bin/env python3
"""Match domain paths without reading domain context."""
import argparse
import json
from pathlib import Path
import re
import sys


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, required=True)
    selection = parser.add_mutually_exclusive_group(required=True)
    selection.add_argument("--prompt")
    selection.add_argument("--domain")
    args = parser.parse_args()
    try:
        root = args.root.expanduser().resolve(strict=True)
        if not root.is_dir():
            raise ValueError("The vault root must be a directory")
        mapping = (root / ".agent-oversight/domains.json").resolve(strict=True)
        if not mapping.is_relative_to(root):
            raise ValueError("The domain map leaves the vault root")
        domains = json.loads(mapping.read_text())["domains"]
        if not isinstance(domains, list) or not domains:
            raise ValueError("domains must be a nonempty list")
        matches = []
        names = set()
        for domain in domains:
            name, relative, keywords = domain["name"], domain["path"], domain["keywords"]
            if not isinstance(name, str) or not name.strip() or name.casefold() in names:
                raise ValueError("Domain names must be nonempty and unique")
            names.add(name.casefold())
            if not isinstance(relative, str) or Path(relative).is_absolute():
                raise ValueError("Domain paths must be relative to the vault root")
            path = (root / relative).resolve()
            if not path.is_relative_to(root) or path == root:
                raise ValueError("A domain path leaves the root or selects the entire vault")
            if not isinstance(keywords, list) or any(not isinstance(k, str) or not k.strip() for k in keywords):
                raise ValueError("Domain keywords must be nonempty strings")
            hits = [k for k in keywords if args.prompt is not None and
                    re.search(r"(?<!\w)" + re.escape(k) + r"(?!\w)", args.prompt, re.IGNORECASE)]
            selected = name.casefold() == args.domain.casefold() if args.domain is not None else bool(hits)
            if selected:
                for filename in ("_context.md", "_log.md"):
                    if not (path / filename).resolve().is_relative_to(root):
                        raise ValueError("A domain file points outside the vault root")
                matches.append({"name": name, "path": str(path), "keywords": hits,
                                "context": str(path / "_context.md"), "log": str(path / "_log.md")})
        status = "matched" if len(matches) == 1 else "ambiguous" if matches else "unmatched"
        print(json.dumps({"status": status, "matches": matches, "context_loaded": False}))
        return 0 if len(matches) == 1 else 1
    except (OSError, ValueError, KeyError, TypeError, RuntimeError) as error:
        print(json.dumps({"status": "error", "error": str(error), "context_loaded": False}))
        return 2


if __name__ == "__main__":
    sys.exit(main())
