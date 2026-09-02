# Agent registry

Every actor in a Bokken run is journaled with kind, name, and (for model
agents) the model that served it. This registry is the authoritative list of
who does what, on which lane, and what each agent may never do.

The tables name the default Anthropic models. For an OpenAI session, the same
actors and routing classes use `gpt-5` on the four frontier lanes
(`research`, `challenge`, `cognition`, `generation`) and `gpt-5-mini` on the
economy lanes `sidekick` and `extraction`. A `--model` override changes only
frontier lanes, so delegated reads and extraction retain the Fusion cost
boundary. Each actor's
journaled `model` is resolved from the session's routing table, so an OpenAI run
attributes these agents to the OpenAI model that served them.

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
| Context retriever | `sidekick` → `claude-sonnet-5`, corpus as cached prefix | Return verbatim source-marked spans for each interview question; truncated output is still used as spans | Paraphrase; answer the question itself; fall back to shipping the full corpus |
| `ui-tester` stepping | `sidekick` → `claude-sonnet-5` | Choose the next browser action (click / fill demo values / navigate) from the interactive-element digest | Activate destructive controls (filtered from the digest); journal a final verdict without frontier confirmation |

The lane pays for mechanical reading, so it runs on the cheapest model the
charter allows for non-extraction work — not on the frontier model whose price
the delegation exists to avoid. The extraction-grade model is not an option
here: every model declares the lanes it may serve, and `claude-haiku-4-5`
declares `extraction` only, so routing it to `sidekick` is refused at session
creation.

Cheapening the lane risks quality, not cost: a model that paraphrases instead
of quoting produces citations the grounding backstop cannot resolve, and those
turns are journaled as abstentions that read like honest research gaps.
`bokken costs <name>` therefore reports persona turns, abstentions, and the
`citation_invalid` share of them, so the regression is legible rather than
silent.

## Extraction lane

| Agent | Routing class → model | Does |
| --- | --- | --- |
| Novelty classifier | `extraction` → `claude-haiku-4-5` | Classify each idea as novel_cluster / variation / duplicate |

## Non-model system actors

| Actor | Kind | Does |
| --- | --- | --- |
| `ui-walker` | system | Real-browser crawl (live DOM + code routes + SPA tabs); observed facts, desktop+mobile screenshots; also exercises generated `wireframe_html` prototypes |
| `panel` | system | Seeded deterministic casting (vivid identities), manifests, contamination firewall |
| `model-router` | agent | Journals every call with class, model, prompt version/hash, usage, cache reads, status |
| Kata (facilitation moves) | agent | Nine budgeted moves, executed or suppressed — both journaled with triggers |
| `report` / dossier / handoff generators | system | Deterministic renderings of the Journal; no model calls except `handoff/specify` |

Two invariants bind them all: persona contributions are always
`confidence_class: simulated`; anything that feeds a `decision.recorded`
runs on a frontier lane.
