# Agent Foundry

Agent Foundry is a small, local control repo for running a supervised AI software company. It sits outside project repos and turns user intent into scoped workspaces, reports, receipts, and safety-checked task cycles.

V0.1 is intentionally mock-safe. It proves the orchestration surface before any real coding worker is allowed to change code.

## Quick Start

```bash
uv sync
uv run pytest
uv run python -m foundry.cli doctor
uv run python -m foundry.cli status
uv run python -m foundry.cli list-agents
uv run python -m foundry.cli list-projects
uv run python -m foundry.cli run-cycle --project ai-trader --task "Inspect repo and suggest next safe build step"
uv run python -m foundry.cli report-latest
```

Pip fallback:

```bash
python -m pip install -e ".[dev]"
python -m pytest
python -m foundry.cli doctor
```

## Mock-Safe Mode

Mock-safe mode is the default. `run-cycle` creates an isolated workspace, writes events, produces a mock inspect-only build result, runs safety review, and writes a report and receipt. It does not run `codex exec`, does not mutate the source project, and does not require `ai-trader` to exist for `status`, `doctor`, or `list-projects`.

## Real Codex Mode

Real Codex mode is not used by default and is not used in tests. The wrapper can build a command shaped like:

```bash
codex exec --full-auto --json -C <workspace> -
```

It only runs when explicitly enabled with configuration or `FOUNDRY_ENABLE_REAL_CODEX=1`. V0.1 never uses `danger-full-access`.

## Unsupported Dangerous Modes

V0.1 does not support:

- `danger-full-access`
- direct mutation of registered project repos
- live trading
- broker execution
- wallet signing
- secret handling
- LangGraph or OpenAI Agents SDK orchestration
- Notion sync
- dashboards
- autonomous overnight loops

## Why Outside AI-Trader

`ai-trader` is a registered project, not the control system. Foundry manages many projects through agent roles, isolated workspaces, safety checks, and receipts. This keeps project code separate from company orchestration.

## Artifacts

Generated runtime output is ignored:

- `workspaces/<project_id>/<task_id>/repo`
- `runs/<task_id>/events.jsonl`
- `runs/<task_id>/task_packet.json`
- `runs/<task_id>/risk_assessment.json`
- `runs/<task_id>/diff.patch`
- `runs/<task_id>/receipt.json`
- `reports/<task_id>.md`
