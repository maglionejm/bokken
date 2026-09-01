# Bokken

> An agentic harness for Design Thinking — one executable, instrumented loop.
> **Test with wood; commit steel when it counts.**

Bokken encodes the **Empathize → Define → Ideate → Prototype → Test** loop as an
executable, event-sourced, governed process. Point it at something tangible — an
app repository, business and performance metrics, interview transcripts — and it
runs the loop either with you in it (**Founder mode**, interactive at the
terminal) or fully autonomously against a governed synthetic persona panel
(**the Dojo**). Every step lands in **the Journal**, an append-only, hash-chained
process ledger, and a finished run produces two deliverables:

1. **The Session Dossier** — outcomes, the process narrative with receipts, and
   the full machine-readable evidence graph.
2. **The handoff** — build-ready **OpenSpec specifications** for the validated
   concept's MVP, ready for a coding agent to ingest and implement.

Terminal-first and MCP-consumable. Python. No GUI.

## Why

Meeting AI documents the past; canvas tools hold sticky notes; app generators
build artifacts without the understanding. Bokken is a harness, not a bot: it
owns the process state, the method library, the evidence, and the audit trail —
so every output can answer *how do you know, who said so, what did we reject,
and why*. In an era of "AI did it", the defensible asset is a replayable account
of the reasoning. That account is the Journal, and it is built in, not bolted on.

## How it works

```
brief + inputs ──► intake ► empathize ► define ► ideate ► prototype ► test ► complete
(repo, metrics,      │         ▲          ▲                             │        │
 interviews)         │         └──────────┴───────── loop-backs ────────┘        │
                     ▼                                                           ▼
              the Journal (append-only, hash-chained JSONL; state = replay)      │
                     │                                                           │
                     ├──► Session Dossier (outcomes · narrative · evidence graph)
                     └──► OpenSpec handoff (MVP specs for a coding agent)
```

- **Stages are a real state machine** with entry/exit criteria and first-class
  loop-backs; every transition is journaled with the evidence that justified it.
- **Facilitation is auditable**: every intervention is a named, budgeted move
  from the **Kata** (reframes, assumption flags, timebox pivots, devil's
  advocate, loop-back proposals…), logged like a tool call — executed or
  suppressed, with reasons.
- **The Dojo is governed simulation**: personas are cast with documented
  sampling and role agents (skeptic, feasibility, viability), answer only from
  the ingested corpus **with citations or abstain** (abstentions become research
  debt), never see the sponsor's preferred answer, and never evaluate work they
  helped create (contamination firewall). Runs stop on budgets, novelty floors,
  or criteria — never on "the answer looked good".
- **Honesty is enforced in code**: synthetic contributions are labeled at the
  record level; decisions resting on simulated or assumed evidence carry
  `requires real validation`; the Dossier states what the run *did not* do; and
  the handoff turns contradicted assumptions into exclusions and validation debt
  into mandatory tasks. None of this is configurable away.
- **Crash-safe by construction**: sessions are durable, named, and resumable;
  kill the process anywhere and `bokken run` continues from the ledger.

## Quickstart

Requires [uv](https://docs.astral.sh/uv/) and Python ≥ 3.12.

```sh
git clone https://github.com/maglionejm/bokken && cd bokken
make install
export ANTHROPIC_API_KEY=...
```

Run the loop autonomously against your product, your numbers, and your research:

```sh
uv run bokken new retention \
  --mode dojo \
  --brief brief.json \
  --repo ./myapp \
  --metrics data/kpis.csv \
  --discussion research/interview-ana.md

uv run bokken run retention          # halts at each stage gate
uv run bokken gate retention approve
uv run bokken run retention          # ... approve gates until:
# halt: completed
# finalization: dossier generated; handoff specs generated

uv run bokken journal retention --type decision   # every decision, with dissent
open .bokken/sessions/retention/dossier/dossier.md
ls   .bokken/sessions/retention/handoff/openspec/changes/
```

Or be the counterpart yourself: `--mode founder` and Bokken interviews *you*,
you pick the winning option, and you score the assumption register.

## The deliverables

**Session Dossier** (`dossier/`): Part A — outcomes with ledger receipts on
every claim; Part B — the process narrative (pivotal moments, why the losers
lost, dissent and how it was handled, loop-backs with triggers); Part C —
`dossier.json`, the full evidence graph (insights↔evidence, idea lineage, IBIS
decision records, persona provenance cards, model traces).

**OpenSpec handoff** (`handoff/`): a strict OpenSpec change package
(`proposal.md`, `design.md`, capability specs with SHALL requirements and
WHEN/THEN scenarios, `tasks.md`) plus `traceability.json` mapping every
requirement to the ledger events it rests on. Copy it into any repo's
`openspec/changes/`, run `openspec validate --strict`, and hand it to your
coding harness. See [docs/handoff.md](docs/handoff.md).

## Surfaces

| | |
| --- | --- |
| **CLI** | `new · run · step · stop · status · list · gate · back · journal · dossier · handoff · serve` — every read verb speaks `--json`; exit codes are stable (0 success, 1 unexpected, 2 refused) |
| **MCP** | `bokken serve` (stdio): 12 tools + 4 resources over the same core with identical result shapes; agent actions are journaled with the client's handshake identity — see [docs/mcp.md](docs/mcp.md) |

## Documentation

| Doc | What it covers |
| --- | --- |
| [docs/architecture.md](docs/architecture.md) | The layer stack, runtime loop, design invariants, blueprint mapping |
| [docs/operating.md](docs/operating.md) | Setup, creating and driving runs, gates, budgets, auditing, deliverables, troubleshooting |
| [docs/events.md](docs/events.md) | The Journal: envelope, hash chain, and the full event taxonomy v1 |
| [docs/handoff.md](docs/handoff.md) | The OpenSpec handoff contract and ingestion workflow |
| [docs/mcp.md](docs/mcp.md) | MCP tools, resources, and client setup |

## Project structure

```
bokken/
├── src/bokken/
│   ├── journal/       # the ledger: schema, store, replay, queries (the moat)
│   ├── orchestrator/  # the DT state machine, runner, gates, budgets
│   ├── stages/        # the five stage engines (both modes)
│   ├── kata/          # the facilitation move library
│   ├── panel/         # persona casting, typed corpus, grounding, firewall
│   ├── models/        # model routing, journaled invocations, prompts
│   ├── dossier/       # Session Dossier generation
│   ├── handoff/       # OpenSpec MVP-spec generation
│   ├── cli/           # the terminal surface
│   ├── mcp/           # the MCP surface
│   └── contract.py    # one result contract for both surfaces
├── openspec/          # bokken's own spec-driven development (10 capabilities)
├── docs/              # documentation + the GitHub Pages site
├── tests/             # 127 tests; the whole loop runs offline against a fake provider
└── scripts/           # live smoke run
```

## Development

```sh
make check    # ruff + pytest + openspec validate --strict  — the definition of done
```

Bokken is built spec-first with [OpenSpec](https://github.com/Fission-AI/OpenSpec)
— the same format it hands off. Every behavior change starts as a change under
`openspec/changes/` and is archived into `openspec/specs/` when implemented.
See [CONTRIBUTING.md](CONTRIBUTING.md) and [CLAUDE.md](CLAUDE.md) (the project
constitution).

Once a concept is selected, an authorized deep web research pass
(`--allow-web-research`) produces a structured market record — competitors
with overlap, sourced signals, regulatory notes, risks — that feeds the
assumption register and the reports.

Models: `claude-fable-5` (effort high, Opus fallback) for research and challenge
agents, `claude-fable-5` (effort high) for execution and documentation too — Opus only as refusal fallback —,
`claude-haiku-4-5` for lightweight signal extraction — every call journaled with
prompt version, token
usage, and request id. The entire test suite runs offline.

## Naming

A *bokken* is the wooden practice sword: you rehearse with wood until failure is
boring, and commit steel only when the risk is understood. Inside the harness:
the **Journal** (the faithful record of how understanding was earned), the
**Kata** (named, drilled, repeatable moves), the **Dojo** (where practice runs
full-contact with no client in the room), and **sparring sessions** (runs
against synthetic participants).

## License

Apache-2.0.
