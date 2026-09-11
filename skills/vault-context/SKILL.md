---
name: vault-context
description: Read one selected vault domain context when you need its current rules, state, or paths.
---

# Read bounded context

Use the supplied vault root and domain name.
Read the root's `.agent-oversight/domains.json` and match the domain name exactly, ignoring letter case.
If the name is missing or ambiguous, ask for the domain before reading context.
Resolve the configured domain path inside the verified vault root. Reject paths or symlinks that leave that root.

Read only that domain's `_context.md`.
Report the source path, relevant current state, and any `last_verified::` date.
An old date means the state needs verification. It does not prove the state is wrong.
If the file is missing, report the missing path. Do not create it during a read request.
Read a deeper file only when it answers a concrete question in the current task.
