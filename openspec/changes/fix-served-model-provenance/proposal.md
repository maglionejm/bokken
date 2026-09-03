# Proposal: fix-served-model-provenance

## Why

Two Journal records describing one contribution disagreed about which model
produced it. `ModelRouter.actor()` stamped `model=self.routing[routing_class]`
— the model routing *asked for* — while the `model.called` record for the very
same contribution correctly carried `"model": served_model or model`, the model
that *answered*. The ledger is the single source of truth and its whole purpose
is honest provenance (Blueprint §2, §3); a contradiction inside it is the worst
kind of defect this project can ship.

They diverge for a configured, expected reason. Per `CLAUDE.md` the research and
challenge classes run on `claude-fable-5` with a **server-side fallback to
`claude-opus-4-8`**, and that fallback exists precisely so it fires under load.
When it does, every persona utterance, researcher finding, and facilitator
record from that call named a model that never ran.

The root cause is the seam. `ModelOutcome` already carried the served model, but
`structured()` returned `outcome.data` and discarded the outcome, so no engine
could reach it. With the served model unreachable, six sites reached past the
seam and indexed the routing table by hand (`router.routing["challenge"]`,
`p.actor(router.routing["cognition"])`, …). Those were not merely untidy: there
is nothing correct for a caller to look up *before* a call, because the served
model is unknowable until it returns.

Nothing in the suite could see any of this. `tests/stages/fake_provider.py`
returned `model=model` — it echoed back whatever it was asked for, making
requested and served identical in every test. That is the same failure shape
this repo has hit before: a charter rule with no mechanical guard, re-violated
by a later feature.

## What Changes

- `Attribution` (in the router, at the seam): the provenance of one completed
  call, carrying the model that answered and building the `Actor` from it.
  `ModelOutcome.attribution` exposes it; `UNATTRIBUTED` is the honest form for
  work no single call produced.
- `structured()` returns `Attributed[T]` — the validated payload welded to that
  provenance (`.data` to use it, `.actor()` to journal it) — rather than a bare
  payload. One function, not two: a parallel `structured_with_outcome()` would
  be a second near-identical path, and duplicated paths drifting apart is this
  codebase's demonstrated failure mode. Because the two travel together there is
  no window in which a caller holds a payload and has to guess its model.
- `Persona.actor()` takes an `Attribution` instead of a bare model string. The
  persona owns its identity (`name`, `persona_id`, which the `Event` validator
  keys `simulated` evidence on); the completed call owns the model. All six
  hand-indexed routing lookups are gone.
- `PersonaTurnGenerator.answer()` returns the turn *with* its attribution and
  the protocol's `model: str` field is dropped — that field could only ever hold
  what routing asked for. The `Interviewer` stamps the turn's own call, backstop
  rewrites included.
- `ModelRouter.actor()` no longer claims a model. Before a call returns the
  router knows only what it asked for; silence is honest where a guess is not.
- Facilitation and deterministic stage mechanics (`FACILITATOR`) claim no model
  either, matching what `kata/registry.py` has always done for moves. Records
  that *are* one call's output — Define's insights and selection, Prototype's
  register and generated artifacts, the UI review, the Test recommendation —
  now name that call's server instead.
- `FallbackProvider` (tests): a fake that answers on a different model than it
  was asked for, on every lane, with `claude-fable-5 → claude-opus-4-8` being
  the charter's own fallback. Plus an end-to-end guard asserting that the set of
  agent-attributed models is a subset of what was served and disjoint from what
  was only requested, and a per-contribution check pairing each Test-stage
  persona reaction with the evaluate call that produced it.

## Capabilities

### New Capabilities

(none)

### Modified Capabilities

- `models`: attribution is derived from the completed call, not the routing
  table; the router itself no longer attributes.
- `stages`: engines journal each contribution with the provenance of the call
  that produced it, and claim no model for work no call produced.

## Impact

`src/bokken/models/router.py`, `src/bokken/stages/base.py`, the seven stage
engines, `src/bokken/panel/{casting,grounding}.py`, and tests under
`tests/{models,panel,stages}/`. No journal schema change: `Actor.model` was
already `str | None`, existing records stay valid, and nothing is migrated.
Nothing derived needed changing — the Dossier and report key on actor *name*
and `persona_id`, never on the model, and cost estimates already priced the
served model from `model.called`.

One site is knowingly left unfixed because it is outside this change's blast
radius: `src/bokken/interview/engine.py` attributes its `assumption.scored`
records via `router.actor("validation-interviewer", "challenge")`, immediately
after the `validate/rescore` call that produced them. With this change those
records name no model rather than the wrong one — honest but understated. The
one-line fix is `outcome.attribution.actor("validation-interviewer")`.
