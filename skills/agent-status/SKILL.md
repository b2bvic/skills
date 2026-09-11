---
name: agent-status
description: Run agent-monitor when you need a local snapshot of Claude process matches and recorded token usage.
---

# Inspect agent status

Locate `agent-monitor` on `PATH`. If it is missing, report the missing tool.
Use the requested output path. Otherwise, choose a new file in the system temporary directory.
If the path already exists, use a new path unless replacement is part of the request.

Run `agent-monitor "/path/to/status.md"` with a safely quoted output path.
Read the generated file before reporting success. A terminal summary alone does not prove the file was written.
Report its path, process matches, session count, token count, and collection time.

The script matches command lines containing `claude`.
Its session totals cover recently modified JSONL files under one discovered project directory.
These counts do not prove agent health, calendar-day usage, or complete account usage.
Do not start, stop, or schedule agents during a status request.
