---
name: gate-check
description: Check a response against an observer-daemon spec and report whether its score meets the configured threshold.
---

# Check response quality

Use the response-file and spec-file paths supplied with `/gate-check`.
If either path is missing, ask for it. Do not guess a private config location.
You need Python 3.11+ and `observer-daemon` on `PATH`.

Run the bundled helper with safely quoted paths:

```bash
python3 "${CLAUDE_SKILL_DIR}/scripts/check.py" --text-file /path/to/response.txt --config /path/to/spec.toml
```

Read its JSON result and exit status. Report the class, score, threshold, and violations.
Exit `0` means the score passes. Exit `1` means the score fails. Exit `2` means the check did not complete.
If the binary, config, or output is invalid, report the error. Never convert an error into a pass.

The observer CLI itself can exit successfully when a score fails. This helper compares the score with `scoring.passing_score`.
A quality pass does not authorize a send, payment, deletion, or publication.
Do not execute an external action from this skill.
