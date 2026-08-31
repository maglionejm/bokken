# Proposal: add-stage-engines

## Why

The orchestrator (add-dt-orchestrator) defines *when* stages run; this change defines *what each stage does* (Blueprint §3.4 stage-by-stage behavior) and wires the LLM layer that powers it (Blueprint §7.1 Models row: frontier model for cognition, cheaper models for signal extraction, every call logged into the ledger). With these engines in place, a session can actually execute Empathize → Define → Ideate → Prototype → Test end-to-end in both Founder and Dojo modes.

## What Changes

- Introduce the five stage engines implementing the `StageEngine` protocol:
  - **Empathize**: adaptive interview program (human founder and/or synthetic panel), evidence capture with provenance, research-debt logging.
  - **Define**: evidence clustering into insights, candidate POV statements, HMW generation, problem-statement selection as an IBIS decision with evidence-coverage scoring.
  - **Ideate**: roundtable protocol — divergence with per-persona quotas and private/public thought separation, novelty monitoring with provocation injection, convergence with pre-frozen criteria and recorded votes, full idea lineage.
  - **Prototype**: assumption register first (riskiest assumption drives fidelity), then artifact generation (concept one-pager, landing copy, storyboard/service blueprint, synthetic demo script) with artifact↔assumption links.
  - **Test**: firewalled fresh-panel evaluation, assumption scoring, kill/iterate/proceed recommendation with confidence, loop-back proposals citing contradicting evidence.
- Introduce model ops: the `ModelRouter` (routing classes → models/params), Anthropic SDK integration, structured outputs, mandatory `model.called` journaling, and budget accounting integration.

## Capabilities

### New Capabilities

- `stages`: the behavior of the five Design Thinking stage engines across Founder and Dojo modes.
- `models`: model routing, invocation logging, structured outputs, and cost accounting for every LLM call in the harness.

### Modified Capabilities

(none)

## Impact

- New code: `src/bokken/stages/`, `src/bokken/models/`.
- New runtime dependency use: `anthropic` SDK (already declared).
- Depends on: `journal`, `orchestrator` (protocol + criteria), `kata` (moves fire inside stages), `panel` (Dojo participation, firewall).
- Requires `ANTHROPIC_API_KEY` at runtime for real runs; tests use a fake router.
