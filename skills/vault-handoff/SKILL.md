---
name: vault-handoff
description: Save a continuation note for one vault domain when a session ends with completed work or open tasks.
---

# Save a domain handoff

Use the supplied vault root and domain name.
Read `.agent-oversight/domains.json` and resolve the domain inside the verified root.
Reject paths or symlinks that leave the root. Ask for a domain if the selection is ambiguous.
Read the domain's `_context.md` and the relevant recent log entries.

Use the vault's configured handoff directory. If none exists, use `Sessions` inside the selected domain.
Create a dated note with a task-specific name. If that name exists, read it before choosing a unique name.
Record completed outcomes, changed files, decisions with reasons, unresolved questions, and the next concrete action.
Distinguish work that shipped from work that remains local or untested.
Do not load unrelated domains or copy their private records into this note.

Apply the vault's author metadata and link conventions. Read back the note and report its path.
If current context needs correction, identify the change. Do not silently replace domain policy during a handoff.
