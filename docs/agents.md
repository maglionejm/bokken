# Agent registry

Every actor in a Bokken run is journaled with kind, name, and (for model
agents) the model that served it. This registry is the authoritative list of
who does what, on which lane, and what each agent may never do.

## Frontier lanes (judgment)

| Agent | Routing class → model | Does | Never does |
| --- | --- | --- | --- |
| Interview personas (`Name (age, city)`) | `research` → `claude-fable-5` (effort high, server-side refusal fallback) | Answer interview questions strictly from corpus slices, with line-span citations; abstain honestly | State uncited facts; lose the `simulated` label |
| Outcome scorer (same personas) | `research` → `claude-fable-5` | Score every desired outcome Importance/Satisfaction 1-10 with reasons for extremes | Validate anything — scoring is hypothesis generation |
| `concept-researcher` | `research` → `claude-fable-5` + server-side web search | Deep web research on the selected concept; every claim carries a source URL | Run without `allow_web_research: true`; emit `observed` evidence |
| `ui-tester` verdict confirmation | `research` → `claude-fable-5` | Confirm each feature verdict (works/broken/unclear) from the step log | Delegate the journaled verdict to the sidekick |
| Convergence lenses (feasibility / viability / desirability) | `challenge` → `claude-fable-5` | Adversarial code review (green/amber/red + first honest slice), independent RICE (firewalled from code), outcome desirability | The RICE lens never sees repository content |
| `skeptic-agent` | `challenge` → `claude-fable-5` | Mandatory on-record challenge before convergence closes | Be skipped; challenge people instead of claims |
| `validation-interviewer` | `research` → `claude-fable-5` | Moderates real humans over a channel (terminal/Twilio): ask, ladder, conclude; rescoring runs on `challenge` | Invent answers; journal a participant as anything but `human`+`reported` |
| Test panel personas | `challenge` → `claude-fable-5` | Score the assumption register against prototype artifacts | Overlap with interview/ideation panels (contamination firewall) |
| `facilitator` | `cognition` → `claude-opus-5` (adaptive, effort high) | Stage mechanics: clustering, candidates, selection, register, fidelity, opportunity algebra | Override budgets; silence dissent |
| Artifact/spec writer | `generation` → `claude-opus-5` (streaming) | Prototype artifacts (Hills + hypotheses), handoff OpenSpec packages with slices and sequencing | Build on contradicted assumptions |

## Sidekick lane (delegated reads — Devin Fusion pattern)

| Agent | Routing class → model | Does | Never does |
| --- | --- | --- | --- |
| Context retriever | `sidekick` → `claude-opus-5`, corpus as cached prefix | Return verbatim source-marked spans for each interview question; truncated output is still used as spans | Paraphrase; answer the question itself; fall back to shipping the full corpus |
| `ui-tester` stepping | `sidekick` → `claude-opus-5` | Choose the next browser action (click / fill demo values / navigate) from the interactive-element digest | Activate destructive controls (filtered from the digest); journal a final verdict without frontier confirmation |

## Extraction lane

| Agent | Routing class → model | Does |
| --- | --- | --- |
| Novelty classifier | `extraction` → `claude-haiku-4-5` | Classify each idea as novel_cluster / variation / duplicate |

## Non-model system actors

| Actor | Kind | Does |
| --- | --- | --- |
| `ui-walker` | system | Real-browser crawl (live DOM + code routes + SPA tabs); observed facts, desktop+mobile screenshots |
| `panel` | system | Seeded deterministic casting (vivid identities), manifests, contamination firewall |
| `model-router` | agent | Journals every call with class, model, prompt version/hash, usage, cache reads, status |
| Kata (facilitation moves) | agent | Nine budgeted moves, executed or suppressed — both journaled with triggers |
| `report` / dossier / handoff generators | system | Deterministic renderings of the Journal; no model calls except `handoff/specify` |

Two invariants bind them all: persona contributions are always
`confidence_class: simulated`; anything that feeds a `decision.recorded`
runs on a frontier lane.
