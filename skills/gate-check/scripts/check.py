#!/usr/bin/env python3
"""Compare observer output with a configured quality threshold."""
import argparse
import json
from pathlib import Path
import re
import subprocess
import sys
import tomllib


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--text-file", type=Path, required=True)
    parser.add_argument("--config", type=Path, required=True)
    parser.add_argument("--binary", default="observer-daemon")
    parser.add_argument("--prompt", default="")
    args = parser.parse_args()
    try:
        config = args.config.expanduser().resolve(strict=True)
        spec = tomllib.loads(config.read_text())
        threshold = spec["scoring"]["passing_score"]
        if type(threshold) is not int or not 0 <= threshold <= 100:
            raise ValueError("scoring.passing_score must be an integer from 0 to 100")
        text = args.text_file.expanduser().read_text()
        if not text.strip():
            raise ValueError("The response file is empty")
        result = subprocess.run(
            [args.binary, "--config", str(config), "--validate", "--prompt", args.prompt],
            input=text, capture_output=True, text=True, timeout=30,
        )
        if result.returncode != 0:
            raise ValueError(f"Observer exited {result.returncode}: {result.stderr.strip()}")
        lines = result.stdout.splitlines()
        class_match = re.fullmatch(r"Class: ([a-z_]+)", lines[0]) if lines else None
        score_match = re.fullmatch(r"Score: (\d+)/100", lines[1]) if len(lines) > 1 else None
        if not class_match or not score_match:
            raise ValueError("Observer output lacks a valid class and score")
        score = int(score_match.group(1))
        if not 0 <= score <= 100:
            raise ValueError("Observer score is outside 0 to 100")
        passed = score >= threshold
        print(json.dumps({
            "status": "pass" if passed else "fail",
            "scope": "response-quality-only",
            "action_authorized": False,
            "class": class_match.group(1),
            "score": score,
            "threshold": threshold,
            "details": "\n".join(lines[2:]),
        }))
        return 0 if passed else 1
    except (OSError, ValueError, KeyError, TypeError, subprocess.TimeoutExpired) as error:
        print(json.dumps({"status": "error", "action_authorized": False, "error": str(error)}))
        return 2


if __name__ == "__main__":
    sys.exit(main())
