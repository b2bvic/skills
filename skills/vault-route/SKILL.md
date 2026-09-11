---
name: vault-route
description: Match a request to configured vault domain paths without loading domain context.
---

# Select a vault domain

Use the explicit vault root and request supplied with `/vault-route`.
If the root is missing, use a verified project root only when the request identifies that project as the vault.
Otherwise, ask for the root.

Run the helper with safely quoted arguments:

```bash
python3 "${CLAUDE_SKILL_DIR}/scripts/route.py" --root /path/to/vault --prompt "plan the sprint"
```

Read `.agent-oversight/domains.json` only when you need to inspect or explain the mapping.
The helper reports matches and paths. It does not read `_context.md` or `_log.md`.
For an explicit domain, use `--domain "Work"` instead of `--prompt`.

Report `matched`, `ambiguous`, `unmatched`, or `error` with the matching evidence.
If multiple domains match, ask which one applies before reading context.
If no domain matches, report that result. Do not invent a mapping or load every domain.
Treat keyword matches as routing hints, not permission boundaries.
