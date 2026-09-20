# Change: add-preflight-estimate

## Why

Cost anxiety is the top adoption blocker (see `add-cost-receipts`, issue #27):
a founder deciding whether to spend real tokens today has to *create and run*
a session before any number appears. `bokken run` frames a flat "$20-35"
guess and `bokken costs` prices the journal *after* the spend. Neither answers
the pre-commitment question: "for **my** brief and **my** panel size, on the
provider/model I'd route to, roughly what will this cost?"

`bokken estimate <brief.json>` answers it by derivation only - no session, no
model calls, no network. It reuses the same three definitions the post-run
surfaces already trust, so the prediction and the eventual receipt speak one
language: the DemoProvider's `USAGE_BY_CLASS` per-routing-class token profile,
the `call_cost_usd` pricing function (honoring the brief's provider/model
routing), and the `functional_bucket` lane split. The output is a deliberately
honest **modeled estimate** - a low-high range, never false precision - so the
founder can decide before paying, and is never misled into treating it as a
guarantee or a measurement.

## What Changes

- **New CLI verb `bokken estimate <brief.json>`** that predicts a run's token
  usage and list-price cost *before* session creation:
  - accepts the same routing knobs `bokken new` accepts - `--panel-size`
    (default 6, matching `bokken new`), `--provider`, `--model` - so the
    estimate matches the session the founder would actually create;
  - performs **derivation only**: no `ModelRouter`, no provider SDK, no
    network, no journal written;
  - prints a **low-high USD range** (not a single false-precision number), a
    **per-functional-lane breakdown** (exploration / research / synthesis) with
    each lane's estimated calls, tokens, and cost, and a plain caveat that the
    figure is a modeled estimate from an illustrative profile, not a
    measurement;
  - makes the **panel-size sensitivity explicit**: more personas mean more
    research-lane calls, so a larger `--panel-size` yields a larger estimate;
  - supports `--json` emitting a stable `EstimateResult` shape for machine
    consumption, one JSON document on stdout.
- **Honesty framing (non-negotiable):** the surface is labeled a "modeled
  estimate", states its assumptions (the panel size assumed and that the token
  profile is the illustrative `USAGE_BY_CLASS` table, not a measurement of this
  brief), and is never presented as a guaranteed or actual cost. It never
  claims to be `bokken costs` (which prices real journaled calls).

## Impact

- Affected specs: `cli` (ADDED requirement: "Estimate verb").
- Affected code (for the implementer; this change writes no `src/`):
  - `src/bokken/cli/app.py` - a new `estimate` verb (guarded, `--json`), taking
    `--panel-size` / `--provider` / `--model` and loading the brief via
    `Brief.model_validate(json.loads(path.read_text()))`.
  - `src/bokken/contract.py` - a new `EstimateResult` shape (the `--json`
    contract, MCP-ready like the other result shapes) carrying the low-high
    range, the per-lane breakdown, the assumptions, and the modeled-estimate
    caveat.
  - `src/bokken/estimate.py` (new helper module) - the derivation, reusing
    existing definitions rather than re-deriving them:
    - the per-routing-class token profile from
      `bokken.demo.provider.USAGE_BY_CLASS`;
    - the pricing function `bokken.report.context.call_cost_usd`, priced on the
      **served** model resolved via `bokken.models.router.resolve_routing`
      (with a `--model` override applied through the same
      frontier-class routing `session_model_config` builds), so the estimate
      honors provider/model exactly as a created session would;
    - the lane split `bokken.report.context.functional_bucket` over the
      prompt-ids a run executes, so the estimate's three lanes reconcile with
      the `bokken costs` functional rollup vocabulary.
  - The low-high range is derived (e.g. a spread band around the modeled point
    estimate), so the range is honest about model variance rather than
    pretending to a single number.
- No journal schema change, no new dependency, no model/network access.
