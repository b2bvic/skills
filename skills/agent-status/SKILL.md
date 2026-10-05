---
name: agent-status
description: Run agent-monitor when you need local Claude Code and Codex process matches, recorded token usage, and coverage warnings.
---

# Inspect agent status

Locate `agent-monitor` on `PATH`. If it is missing, report the missing tool.
Use the requested output path. Otherwise, choose a new file in the system temporary directory.
If the path already exists, use a new path unless replacement is part of the request.

Run `agent-monitor "/path/to/status.md"` with a safely quoted output path.
Read the generated file before reporting success. A terminal summary alone does not prove the file was written.
Report its path, process matches, session count, token count, and collection time.

Check `agent-monitor --help` before using an installed version.
The current source matches Claude and Codex executable names and interpreter script paths.
It discovers Claude projects and Codex session directories, then selects recorded usage by event timestamps.
Report unknown or partial coverage alongside counts. Cumulative usage can remain an upper bound when a baseline is missing.
These observations do not prove task completion, complete account usage, billing totals, or remaining subscription allowance.
Do not start, stop, or schedule agents during a status request.
