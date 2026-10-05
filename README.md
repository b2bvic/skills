# Claude Code agent oversight skills: skills

This repository installs Claude Code skills for operators who inspect agent sessions and local artifacts from hosted-model workflows.
The helpers expose session searches, explicit context selection, and evidence checks when completion claims need verification.

[Project page](https://scalewithsearch.com/code/skills)

## Install

Use Git, Python 3.11 or newer, and Claude Code.
The installer copies eight skill folders and refuses existing destination names before copying.
It does not change hooks, permissions, or schedules.

```bash
git clone https://github.com/b2bvic/skills.git b2bvic-skills
cd b2bvic-skills
python3 install.py
```

For a project installation, pass `--dest /path/to/project/.claude/skills`.
Install `ledger`, `agent-monitor`, and `observer-daemon` separately when the corresponding skills need them.

## Quick start

Run a context selection helper without installing skills or reading context bodies:

```bash
demo_record=$(mktemp -d)
mkdir -p "$demo_record/.agent-oversight"
cat > "$demo_record/.agent-oversight/domains.json" <<'JSON'
{"domains":[{"name":"Work","path":"Work","keywords":["release"]}]}
JSON
python3 skills/vault-route/scripts/route.py --root "$demo_record" --prompt "review the release"
```

The helper returns `matched`, the selected paths, and `context_loaded: false`.
It does not need an existing context body to select a path.

## How it works

These agent context management skills are patterns a team can adopt with its own domain map and approval integration.

| Skill | Purpose |
|---|---|
| `/ledger-search` | Search an initialized session-ledger database. |
| `/agent-status` | Generate and inspect a process dashboard. |
| `/gate-check` | Compare a configured observer score with a threshold. |
| `/completion-check` | Check declared local artifacts and an optional expected Git HEAD. |
| `/vault-route` | Select domain paths without reading context bodies. |
| `/vault-context` | Read the domain context you select. |
| `/vault-log` | Append verified work to a selected domain log. |
| `/vault-handoff` | Save a continuation note in the selected domain. |

Claude Code session search requires an initialized, harvested ledger.
`gate-check` reports response quality; `completion-check` performs agent artifact verification from an explicit JSON contract.
The completion helper supports existence, SHA-256, and exact JSON checks.
Its receipt retains observed values, hashes, check status, and the optional Git HEAD comparison.

Run the synthetic regressions:

```bash
python3 -m unittest discover -s tests -v
```

## Limits

- Skill text guides the model. It does not enforce permissions or execute an approval gate.
- A passing writing score does not prove task completion. Both check helpers retain `action_authorized: false`.
- Completion checks evaluate declared local artifacts. Outcome labels do not certify deployment, external acceptance, or task completion.
- A Git HEAD match verifies the reference. It does not verify working-tree contents or installed code.
- Age checks use contract-supplied timestamps. They do not authenticate evidence or establish when a file changes.
- Concurrent changes are outside the completion helper’s isolation guarantees.
- Routing reports ambiguous or unmatched requests and leaves context unloaded. You must choose a domain before reading context.
- The installer targets Claude Code skill folders. It does not install a Codex CLI adapter.

## Related repositories

- [agent-oversight](https://github.com/b2bvic/agent-oversight): orchestration cluster and evaluation guide.
- [session-ledger](https://github.com/b2bvic/session-ledger): transcript archive and search.
- [agent-monitor](https://github.com/b2bvic/agent-monitor): process and usage observations.
- [observer-daemon](https://github.com/b2bvic/observer-daemon): response writing checks.
- [route-domain](https://github.com/b2bvic/route-domain): example hook that loads context bodies.

## License

[MIT](LICENSE).
