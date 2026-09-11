---
name: vault-log
description: Append verified session outcomes to one configured vault domain log when the user asks to record completed work.
---

# Log verified work

Use the supplied vault root and domain name.
Read `.agent-oversight/domains.json` and resolve the selected domain inside the verified root.
Reject paths or symlinks that leave the root. Ask for a domain if the selection is ambiguous.

Read that domain's `_log.md` before editing it. Preserve its date format and entry order.
Append a new entry with completed outcomes, affected file paths, decisions, and remaining work.
Use only facts supported by this session or source files. Separate verified outcomes from untested claims.
Do not rewrite earlier entries or copy private material from other domains.
If the log is missing, create it only when the request includes creating the domain log.

Read back the entry and report the file path. Apply the vault's existing author metadata and link conventions.
