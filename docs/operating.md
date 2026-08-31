# Operating Bokken

## Setup

```sh
make install                     # uv sync
export ANTHROPIC_API_KEY=...     # required for real runs (not for tests)
export BOKKEN_HOME=~/bokken-work # optional; default workspace is ./.bokken
```

Sessions live in `$BOKKEN_HOME/sessions/<slug>/` (or `./.bokken/sessions/` in
the directory you run from — like git, workspace-local by default).

## Creating a session

Give Bokken something tangible to start from: the app repo, the numbers, and
what humans have said.

```sh
bokken new retention \
  --mode dojo \
  --brief brief.json \
  --repo ./myapp \
  --metrics data/kpis.csv \
  --discussion research/interview-ana.md --discussion research/interview-luis.md \
  --budget 500000 \
  --panel-size 8 --seed 42
```

`brief.json`:

```json
{
  "problem_space": "commuter shuttle retention",
  "constraints": ["no new hardware"],
  "target_segments": ["commuters", "operators"],
  "success_criteria": ["validated demand", "churn below 5%"],
  "risk_tolerance": "medium"
}
```

Without `--brief`, `bokken new <name>` runs an interactive intake. Modes:

- `--mode founder` — you are the counterpart: Bokken interviews you, you pick
  the winning option, you score assumptions. Gates default to `none`.
- `--mode dojo` — fully autonomous against the synthetic panel. Gates default
  to `stage_boundaries`: the run halts before every stage transition until you
  approve.

Gate policy is tunable at creation: `--gates none`,
`--gates stage_boundaries`, or `--gates define,test` (only those boundaries).

## Driving a run

```sh
bokken run retention        # advance to the next halt
bokken status retention     # where am I, what blocks progress
```

`run` always returns at a **halt**:

| Halt | Meaning | What you do |
| --- | --- | --- |
| `gate_pending` | a stage boundary needs sign-off | `bokken gate retention approve` (or `reject --reason "..."` — the run stays in the stage for rework) |
| `input_pending` | Founder mode needs your answer | run `bokken run` interactively and answer the prompt |
| `stopped` | budget exhausted, novelty floor, or human stop | raise the budget on resume, or leave it |
| `completed` | the loop finished | `bokken dossier retention` |

Other controls:

```sh
bokken step retention                          # at most one stage, then return
bokken stop retention --reason "enough for today"
bokken back retention define --reason "test contradicted insight"   # loop back
bokken list                                    # all sessions in the workspace
```

Everything is resumable: kill the process at any point (Ctrl-C included) and
`bokken run` continues from the journal. A budget-exhausted session resumes
after a human raises the budget — this is the only config a human can change,
and it is journaled:

```sh
# budgets are raised on resume via the core; from the CLI simply re-run after
# creating with a higher budget, or drive it over MCP / Python:
# Runner.for_session("retention").run(config_overrides={"budgets": {"total_tokens": 1_000_000}}, actor=human)
```

## Watching and auditing

```sh
bokken journal retention --follow                      # tail the ledger live
bokken journal retention --type decision               # every decision, with dissent
bokken journal retention --type option --stage ideate  # the idea lineage
bokken journal retention --type model                  # every LLM call: model, prompt version, tokens
bokken journal retention --type facilitation           # every Kata move executed/suppressed
bokken journal retention --json | jq ...               # canonical JSONL for scripts
```

## The deliverables

The process does not stop at the Dossier: a completed run is **finalized
automatically** — Dossier first, then build-ready OpenSpec specifications for
the validated concept (the handoff). Both can also be produced on demand:

```sh
bokken dossier retention
bokken handoff retention
```

**Dossier** — `dossier/dossier.md` (Part A outcomes + Part B process narrative +
honesty section) and `dossier/dossier.json` (Part C — the full machine-readable
evidence graph). Works mid-run too (labeled *partial*). Dojo dossiers always
open with the simulated-run banner; decisions resting on synthetic evidence
carry `requires real validation` — neither can be turned off.

**Handoff** — `handoff/` contains a strict OpenSpec change package
(`openspec/changes/build-mvp-<slug>/` with proposal, design, capability specs,
tasks) plus `traceability.json` mapping every requirement back to ledger events,
ready for a different harness component (e.g. a coding agent) to ingest: copy
the change into the target repo's `openspec/changes/`, run
`openspec validate --strict`, implement with `/opsx:apply`. Honesty carries
over: contradicted assumptions never become requirements (they are design
exclusions), and untested / simulated-evidence items become mandatory
real-world validation tasks. Refused when there is no convergence decision or
the recommendation is `kill`.

## Operating over MCP

```sh
claude mcp add bokken -- uv run --directory /path/to/bokken bokken serve
```

Then any MCP client can drive the same loop: `create_session_tool` →
`run_session` → (`resolve_gate` | `submit_input`) → … → `generate_dossier`.
Founder-mode questions surface as `input_pending` with a `pending_question_id`;
answer with `submit_input` and run again. Agent actions are journaled with the
client's handshake identity — the ledger always shows who (human or agent)
approved what. See `docs/mcp.md` for the full tool/resource table.

## Scripting (`--json` contract)

Every read verb supports `--json` (single JSON document on stdout, errors on
stderr). Exit codes: `0` success including clean halts, `1` unexpected error,
`2` invalid/refused (unknown session, illegal transition, validation failure).

```sh
until [ "$(bokken run retention --json | jq -r .halt)" = "completed" ]; do
  bokken gate retention approve
done
bokken dossier retention --json | jq -r .markdown_path
```

## Configuration reference

Everything is fixed at `bokken new` and journaled in the `session.created`
config snapshot. After creation, only **budgets** may change — by a human, on
resume, journaled (`session.resumed` with `config_overrides`); the brief, gate
policy, and success criteria are immutable (no-silent-self-escalation).

| Setting | Where | Values / default |
| --- | --- | --- |
| Mode | `--mode` | `founder` (interactive) / `dojo` (autonomous). |
| Gate policy | `--gates` | `none` (founder default) · `stage_boundaries` (dojo default) · CSV of stages, e.g. `define,test` |
| Token budget | `--budget` | total tokens for the run; per-class sub-budgets (`cognition_tokens`, `extraction_tokens`, `generation_tokens`) available at the core level |
| Panel | `--panel-size`, `--seed` | defaults 6 and 7; casting is deterministic per (brief, seed) |
| Inputs | `--repo`, `--metrics`, `--discussion`, `--doc` | typed corpus sources; all repeatable except `--repo` |
| Model routing | core `config.routing` | per-class overrides within the allowlist (`claude-opus-4-8`, `claude-opus-4-7`, `claude-sonnet-4-6`, `claude-haiku-4-5`); defaults: cognition/generation → opus-4-8, extraction → haiku-4-5 |

**Brief format** (`--brief brief.json`):

```json
{
  "problem_space": "one sentence on the space, not a solution",
  "constraints": ["hard constraints the run must respect"],
  "target_segments": ["who must be heard; drives interview coverage"],
  "success_criteria": ["what a good outcome looks like"],
  "risk_tolerance": "low | medium | high",
  "inputs": {
    "repo": "path/to/app",
    "metrics": ["kpis.csv"],
    "discussions": ["interview-a.md"],
    "documents": ["market-note.md"]
  }
}
```

All `inputs` are optional — a blank-page run is legal — but tangible inputs are
what let personas cite the product as it exists (`code`), the numbers
(`metrics`), and real human voices (`discussion`).

## Development operations

```sh
make check                    # ruff + pytest + openspec validate --strict (definition of done)
uv run pytest -q              # offline: the whole loop runs against a fake provider
uv run python scripts/smoke_run.py   # one tiny live run against the real API
```

Behavior changes go through OpenSpec: `/opsx:propose` → spec deltas →
`/opsx:apply` → `/opsx:archive`. Main specs live in `openspec/specs/`.

## Troubleshooting

- `session is locked` — another process holds the session for writing; wait or
  stop it. Reads (`status`, `journal`, `dossier`) never need the lock.
- `engine for <stage> ran N times without meeting the exit criteria` — the
  stage cannot legitimately finish (e.g. Define with zero evidence because all
  interviews abstained). Add inputs (`--repo/--metrics/--discussion`), answer
  the research debt, or loop back.
- Verify ledger integrity any time: chain verification runs on open; tampering
  is reported with the first broken sequence number.
