# Change: refine-exploration-mining

## Why

Adapted from the legacy-reengineering discipline in "build-software-with-style"
(analyst-verified): a mined capability map is only trustworthy when its
citations are readable, contestable, and priced. Today the capability map
journals bare line spans nobody can eyeball, the founder never gets to
confirm or dispute what the machine read into their code, the map never
surfaces in any deliverable, the product's own vocabulary is lost between
exploration and the specs, and exploration spend is indistinguishable from
research spend.

## What Changes

- Quoted spans: every validated capability citation is journaled with a
  deterministic, truncated (<=200 chars) verbatim quote of the resolved
  corpus span, inside the existing `citations` extension key. Label stays
  "cited", never "proven". No model calls.
- Founder ratification: in founder mode only, after the capability map is
  produced, the founder is asked per capability (confirm / dispute / skip,
  accepting c/d/s). Confirm marks the interpretation with the declared
  extension key `ratified: true`; dispute marks it `ratified: false` and
  appends the founder's correction as human `reported` evidence ref'ing the
  interpretation; skip journals nothing. Dojo runs are unchanged;
  `InputRequired` propagates like every other founder ask.
- Map in deliverables: the HTML report renders a "What the product does
  today" block (statements, quotes, honest flags: `(ungrounded)`,
  `(disputed by founder)`), and the dossier's Part A lists one line per
  capability. Deterministic renderings, no model calls.
- Cited glossary: the same capability-map call also asks for up to 10 domain
  terms (the product's own vocabulary) with citations; terms are journaled
  as `interpretation.derived` kind `domain_term` with validated citations
  and quotes, and a rendered glossary is threaded into `define/cluster` and
  `handoff/specify` prompts ("(no glossary)" when absent).
- Exploration cost split: the costs verb and the `cost_report` MCP payload
  add a three-line functional rollup (exploration / research / synthesis)
  aggregated from the existing cost rows by prompt-id prefix; the rollup
  sums to the run total. Pure aggregation.

## Impact

- Affected specs: `stages` (MODIFIED Code exploration), `report` (ADDED
  current-capability section), `dossier` (MODIFIED Part A), `cli` (MODIFIED
  Costs verb; the MCP `cost_report` shape follows the CLI `--json` contract)
- Affected code: `stages/exploration.py`, `stages/empathize.py`,
  `stages/define.py`, `stages/schemas.py`, `handoff/generate.py`,
  `journal/schema.py` (kind literal + `ratified` extension key),
  `dossier/model.py`, `dossier/render.py`, `report/context.py`,
  `report/page.py`, `cli/app.py`, `mcp/server.py`, `models/prompts.py`
  (capability_map v3, cluster v3, specify v4), `demo/provider.py`,
  `tests/stages/fake_provider.py`
