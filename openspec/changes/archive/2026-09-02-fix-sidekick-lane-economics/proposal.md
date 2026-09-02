# Proposal: fix-sidekick-lane-economics

## Why

The sidekick lane exists so that frontier prices are paid only for judgment: it
handles deliberately mechanical work (verbatim corpus spans for an interview
question, the next browser click from an element digest). On the Anthropic
table it routed to `claude-opus-5` — tied for the most expensive model in the
registry — so the delegated read cost the same per token as the judgment it was
meant to protect, and the Fusion pattern was defeated on the default provider
(Blueprint §5). The OpenAI table already routed the lane to its mini model.

Two related gaps close with it. The registry's capability guard was a single
`frontier` flag, so it only protected the four judgment lanes:
`resolve_routing({"sidekick": "claude-haiku-4-5"})` was accepted even though
CLAUDE.md reserves the extraction-grade model for the extraction class. And a
cheaper delegated read fails silently rather than loudly — a model that
paraphrases instead of quoting produces citations the grounding backstop cannot
resolve, and those turns land as abstentions indistinguishable from honest
research gaps, so a quality regression would present itself as integrity.

## What Changes

- Route the Anthropic `sidekick` lane to `claude-sonnet-5`, the cheapest
  charter-compatible model for non-extraction work (2.0/10.0 against 5.0/25.0
  per MTok). OpenAI lane economics are unchanged.
- Replace the registry's boolean `frontier` capability with an explicit set of
  routing classes each model may serve, derived from the journal's
  routing-class taxonomy, and refuse any class a model does not declare — so
  the charter's extraction-only reservation for `claude-haiku-4-5` holds
  mechanically on the sidekick lane too, not only on the judgment lanes.
- Report grounding health next to lane economics: `bokken costs` and the MCP
  `cost_report` gain persona turns, abstentions, and the share of abstentions
  the backstop forced through invalid citations, so a cheaper lane can be
  compared before and after on quality as well as on price.

## Capabilities

### New Capabilities

(none)

### Modified Capabilities

- `models`: lane capability per model plus economical Anthropic sidekick routing.
- `cli`: the costs report carries grounding health alongside spend.

## Impact

`src/bokken/models/router.py`, `src/bokken/panel/grounding.py` (a derived read,
no new events), the CLI and MCP cost surfaces, `docs/agents.md`,
`docs/operating.md`, and routing, panel, and CLI tests.

The `models` delta is written on top of the `add-openai-support` delta of the
same requirement (that change is not archived yet), so it must be archived
after it.

## Constitution note (not applied)

`CLAUDE.md` does not name the sidekick lane, which is how the charter and the
code came to disagree here. Proposed wording for the Stack paragraph, to be
applied by a maintainer rather than unilaterally — replacing "`claude-haiku-4-5`
only for the lightweight extraction routing class":

> the delegated `sidekick` lane (verbatim corpus reads, mechanical UI stepping)
> on `claude-sonnet-5`; `claude-haiku-4-5` only for the lightweight extraction
> routing class and never on any other lane.
