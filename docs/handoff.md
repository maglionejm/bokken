# The handoff: OpenSpec specs from a validated run

The run does not stop at the Dossier. Once a concept has survived the loop, the
handoff turns it into **build-ready OpenSpec specifications** — the bridge
between "we validated this idea" and "an agent is implementing it". The Dossier
is the account of what was learned; the handoff is the steel drawing.

## When it happens

- **Automatically**: when a run reaches `complete`, the surfaces finalize the
  session — Dossier first, then handoff — skipping whatever already exists
  (idempotent). The run result reports it:
  `finalization: dossier generated; handoff specs generated`.
- **On demand**: `bokken handoff <name>` or the `generate_handoff` MCP tool.
- **Refused** (nothing written): when the session has no convergence decision,
  or when the test recommendation is `kill` — a killed concept has no build
  handoff.

## Package layout

```
<session>/handoff/
├── README.md                       # what this is + ingestion steps
│                                   # (Dojo runs: SIMULATED VALIDATION banner)
├── traceability.json               # requirement → ledger event ids
└── openspec/changes/build-mvp-<session>/
    ├── proposal.md                 # why (from the run) / what changes / capabilities
    ├── design.md                   # context, decisions, and EXCLUSIONS
    ├── specs/<capability>/spec.md  # Purpose + ADDED Requirements (SHALL + scenarios)
    └── tasks.md                    # implementation tasks + mandatory validation tasks
```

## What goes in — and what is kept out

Generation reads the journal-derived model (problem statement, winning concept,
assumption register with test scores, artifacts) and makes **one journaled
model call** to draft the spec package; everything after that is deterministic
rendering with structural validation. The honesty rules are code, not prompt:

| Run fact | Where it lands |
| --- | --- |
| Supported assumption | may ground requirements (mapped in `traceability.json`) |
| **Contradicted** assumption | **never a requirement**; listed in `design.md` as `Do NOT build on: …` with its ledger id |
| Untested assumption | a mandatory task under `## Real-world validation (mandatory)` |
| Recommendation flagged `requires_real_validation` | validation tasks for every supported-but-simulated assumption |
| Dojo mode | README banner: validated against a synthetic panel, not real users |

Any requirement the model drafts on top of a contradicted assumption is dropped
in normalization; if nothing survives, generation fails rather than writing a
hollow package.

## Format guarantees

The package is written only if it passes a structural validator mirroring
OpenSpec's strict rules: kebab-case capability directories; `## Purpose`
(≥ 50 chars) + `## ADDED Requirements`; every requirement a
`### Requirement:` with a SHALL statement and at least one
`#### Scenario:` with `- **WHEN**` / `- **THEN**`; numbered checkbox tasks,
each stating its verification. Weak model output is repaired deterministically
(normative phrasing, scenario scaffolds) before validation. A generated package
has been verified to pass the real `openspec validate --strict` after ingestion
into a fresh repository.

## Ingesting into a target repository

```sh
cd target-repo
openspec init                          # once, if the repo has no openspec/
cp -r <session>/handoff/openspec/changes/build-mvp-<slug> openspec/changes/
openspec validate --strict             # should pass as generated
# then implement with your coding harness, e.g. in Claude Code:
#   /opsx:apply build-mvp-<slug>
#   /opsx:archive build-mvp-<slug>
```

`traceability.json` travels with the package: when a reviewer asks *why is this
a requirement?*, every requirement resolves to the assumption events, and every
exclusion to the contradicting test evidence, in the originating session's
Journal — which stays available alongside the run's `dossier/`.

## Auditing a handoff

Everything about the generation itself is in the ledger:

```sh
bokken journal <name> --type model | grep handoff/specify   # the generation call
bokken journal <name> --type artifact --json \
  | jq 'select(.payload.kind=="handoff_package") | .payload'
```

The `handoff_package` event carries the change id and capability list, and its
`refs` point at the problem-statement, concept, and recommendation decisions it
was built from.
