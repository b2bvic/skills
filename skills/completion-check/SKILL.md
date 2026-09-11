---
name: completion-check
description: Verify declared local completion evidence from a JSON contract of artifact existence, sha256 or JSON-value checks, and an optional expected Git HEAD. Use when the user runs /completion-check or asks whether local artifacts prove a task is complete.
---

# Check completion evidence

Use the contract path supplied with `/completion-check`. If it is missing, ask for it.
Do not infer completion from model prose, process status, a quality score, or helper exit status alone.

This skill does not replace `/gate-check`. Quality scoring is a separate check.
Neither skill authorizes a send, payment, deletion, or publication.

Run the bundled helper with a safely quoted path:

```bash
python3 "${CLAUDE_SKILL_DIR}/scripts/check.py" --input /path/to/contract.json
```

Read the JSON receipt. Exit `0` means every declared local check passes.
Outcome and claim text are labels, not executable acceptance criteria.
`expected_outcome_status` stays `not_evaluated`; `task_completion_verified` stays false.
Exit `1` means `failed` or `unverified`. Exit `2` means the contract or a path check did not complete.
Missing, unreadable, stale, or malformed evidence is never verified.
`action_authorized` is always false. Do not execute an external action from this skill.

The contract declares an absolute `workspace_root`, `expected_outcome`, and `checks`.
Each check needs `id`, `kind`, `claim`, `scope`, and a relative `path`.
Kinds are `existence`, `sha256`, and `json_value`.
Optional `source_revision` pins `expected_head` for a local Git repo inside the workspace.
Optional evidence timestamps and `max_age_seconds` are compared with check time UTC.
Sanitized contract shapes are in `examples/`. Replace placeholder roots, hashes, revisions, and timestamps before use.
The missing, wrong, stale, wrong-revision, and repeat-checks examples are negative cases.
The repeat-checks example is invalid because it repeats a check identifier.

Report expected vs observed values, source path, hash, revision, and the tested claims only.
Do not treat a weaker verified check as proof of a stronger expected outcome.
The helper reads only declared local files. It does not run other commands or fetch URLs.

A Git HEAD match verifies only the recorded reference. It does not verify working-tree contents or installed code.
Age checks compare contract-supplied timestamps. They do not authenticate evidence or establish when a file changes.
JSON checks compare types and values from the same bytes used for the receipt hash.
Concurrent file changes are outside this helper’s isolation guarantees.
