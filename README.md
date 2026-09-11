# Agent oversight skills

You can repeat searches, miss running agents, load the wrong vault context, or treat a quality score as completed work.
Use these Claude Code skills to run local checks and retrieve the relevant records.

## Install

You need Git, Python 3.11+, and Claude Code. Install the skills with one command:

```bash
git clone https://github.com/b2bvic/skills.git b2bvic-skills && python3 b2bvic-skills/install.py
```

The installer copies eight skill folders into `~/.claude/skills`.
It refuses existing names before copying. It does not change hooks, permissions, or schedules.
For a project installation, run `python3 install.py --dest /path/to/project/.claude/skills` from this repository.

| Skill | Use |
|---|---|
| `/ledger-search authentication bug` | Search an existing session-ledger database. |
| `/agent-status ./status.md` | Write and inspect a local process dashboard. |
| `/gate-check ./response.txt ./spec.toml` | Compare an observer score with your configured threshold. |
| `/completion-check ./contract.json` | Verify declared local artifacts and an expected Git HEAD. |
| `/vault-route /path/to/vault plan the sprint` | Match a request to domain paths without loading context. |
| `/vault-context /path/to/vault Work` | Read the selected domain context. |
| `/vault-log /path/to/vault Work` | Append verified work to the selected domain log. |
| `/vault-handoff /path/to/vault Work` | Save a continuation note inside the selected domain. |

Each folder contains `SKILL.md`. Claude can also select a relevant skill from your request.
See the [Claude Code skill documentation](https://code.claude.com/docs/en/skills) for discovery and invocation.

## Tool setup

Install [session-ledger](https://github.com/b2bvic/session-ledger), [agent-monitor](https://github.com/b2bvic/agent-monitor), and [observer-daemon](https://github.com/b2bvic/observer-daemon) separately.
Put `ledger`, `agent-monitor`, and `observer-daemon` on your `PATH`.
Initialize and harvest your ledger before searching. Configure an observer spec before checking responses.

`gate-check` checks response quality only. It does not prove that work is complete, and it does not authorize or execute an external action.
The helper returns `0` for a passing score, `1` for a failing score, and `2` for a check error.

`completion-check` checks explicit local artifacts and an optional expected Git HEAD against a JSON contract. It does not infer completion from model prose or process status, and it does not authorize or execute an external action.
The helper returns `0` when all declared local checks pass, `1` for failed or unverified checks, and `2` for errors.
Outcome and claim text are labels. The helper does not evaluate their meaning.
`expected_outcome_status` stays `not_evaluated`; `task_completion_verified` stays false.
A verified status covers only the concrete checks shown in the receipt.

You must enforce action approval in your own integration. Neither helper is an approval gate.

## Vault setup

The vault skills adapt the public [Owned Record routing pattern](https://github.com/b2bvic/owned-record/blob/main/docs/context-routing.md).
They use your domain names and paths. They do not install automatic context-injection hooks.

Create `.agent-oversight/domains.json` inside your vault using this structure:

```json
{
  "domains": [
    {"name": "Work", "path": "01 - Work", "keywords": ["sprint", "project", "meeting"]},
    {"name": "Personal", "path": "02 - Personal", "keywords": ["household", "journal"]}
  ]
}
```

Each domain directory contains `_context.md` and `_log.md`.
The router returns paths and matches. It never reads those files.
When a request matches multiple domains, you choose the domain before context loads.

Logging and handoff skills adapt the public Owned Record [log](https://github.com/b2bvic/owned-record/blob/main/.claude/commands/log.md) and [handoff](https://github.com/b2bvic/owned-record/blob/main/.claude/commands/handoff.md) procedures.
You keep existing vault formatting and approval rules.

## Verify

Run `python3 -m unittest discover -s tests -v` from this repository.
The tests use temporary fixtures and do not access your live ledger or vault.

A Git HEAD match verifies only the recorded reference. It does not verify working-tree contents or installed code.
Age checks compare contract-supplied timestamps. They do not authenticate evidence or establish when a file changes.
JSON checks compare types and values from the same bytes used for the receipt hash.
Concurrent file changes are outside this helper’s isolation guarantees.
