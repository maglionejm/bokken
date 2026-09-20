# Tasks: add-preflight-estimate

## 1. Estimate helper (derivation)

- [ ] 1.1 Add `src/bokken/estimate.py`: derive a run's per-routing-class call
  counts from the executed prompt set, scaling the research lane with panel
  size (per-persona research-lane calls), with no model calls or network.
- [ ] 1.2 Multiply call counts by the per-routing-class token profile
  (`bokken.demo.provider.USAGE_BY_CLASS`) and price each class on its served
  model via `resolve_routing(...)` (provider + `--model` override applied as
  `session_model_config` would) through `report.context.call_cost_usd`.
- [ ] 1.3 Split the priced calls into exploration / research / synthesis with
  `report.context.functional_bucket`; assert the three lane costs sum to the
  point estimate.
- [ ] 1.4 Produce a low-high range as a spread band around the point estimate
  (honest variance, not false precision), plus the stated assumptions
  (panel size, profile source) and the modeled-estimate caveat text.

## 2. Contract shape

- [ ] 2.1 Add `EstimateResult` to `src/bokken/contract.py`: `cost_low_usd`,
  `cost_high_usd`, point estimate, per-lane breakdown (calls/tokens/cost),
  assumptions, and the modeled-estimate caveat string.

## 3. CLI verb

- [ ] 3.1 Add the `estimate <brief.json>` verb to `src/bokken/cli/app.py`
  (`@guarded`, `--panel-size` default 6, `--provider`, `--model`, `--json`),
  loading the brief via `Brief.model_validate(json.loads(...))`.
- [ ] 3.2 Human output labels the figure a modeled estimate, states assumptions,
  and points to `bokken costs`; `--json` emits one `EstimateResult` document on
  stdout, stderr empty, exit 0.
- [ ] 3.3 A missing/invalid brief exits 2 to stderr before any derivation; no
  session or journal is written.

## 4. Tests and check

- [ ] 4.1 Tests: range low <= high; lanes sum to the point estimate; larger
  `--panel-size` yields a strictly larger cost and research-lane call count;
  `--provider openai`/`--model` change the priced model; missing brief exits 2;
  `--json` shape is stable and stderr is empty.
- [ ] 4.2 `make check` green (ruff + pytest + `openspec validate --strict`).
