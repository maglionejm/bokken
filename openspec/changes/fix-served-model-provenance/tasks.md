# Tasks

- [x] 1.1 Add `Attribution` (served model → `Actor`), `UNATTRIBUTED`, and
  `Attributed[T]` to `models/router.py`, plus `ModelOutcome.attribution`;
  verified by
  `tests/models/test_router.py::test_actor_provenance_names_the_model_that_answered`
  and `::test_attributed_carries_data_and_provenance_together`.
- [x] 1.2 Strip the model claim from `ModelRouter.actor()` so routing can no
  longer stamp a requested model onto a contribution; verified by
  `tests/models/test_router.py::test_router_actor_claims_no_model`.
- [x] 2.1 Make `structured()` return `Attributed[T] | None` — one helper, no
  parallel payload-only path — and replace `facilitator(router)` with a
  model-less `FACILITATOR`; verified by the full offline dojo and founder e2e
  runs, which exercise all twenty call sites.
- [x] 2.2 Take an `Attribution` in `Persona.actor()` and delete the six
  hand-indexed `router.routing[...]` lookups in `persona_gen`, `ideate`,
  `testing`, and `empathize`; verified by
  `grep -rn 'router.routing\[' src/bokken/stages src/bokken/panel` returning
  nothing and by `tests/panel/test_panel.py` asserting the persona actor names
  the generator's served model.
- [x] 2.3 Return the turn with its attribution from `PersonaTurnGenerator`,
  dropping the protocol's `model` field, and stamp it in the `Interviewer`
  including backstop-forced abstentions; verified by
  `tests/panel/test_panel.py::test_invalid_citation_is_converted_to_abstention`
  and `::test_grounded_answer_is_simulated_with_citations`.
- [x] 2.4 Attribute each engine record to the call that produced it, and give
  facilitation, deterministic tallies, rendered files, and the un-dispatched
  research refusal no model; verified by the e2e assertion that
  `facilitation.move_executed` appears among the model-less agent records and
  by the full offline runs.
- [x] 3.1 Add `FallbackProvider` to `tests/stages/fake_provider.py`, answering
  on a different same-provider model on every lane; verified by its own
  assertions (it refuses to echo a request back) and by the e2e premise check
  that served and requested models are disjoint.
- [x] 3.2 Add the mechanical guard: a full offline run under `FallbackProvider`
  asserting agent-attributed models ⊆ served and disjoint from requested-only,
  plus per-contribution pairing of Test-stage persona records with their
  evaluation call; verified by
  `tests/stages/test_engines_e2e.py::test_agent_provenance_names_the_model_that_answered`,
  and confirmed to fail when a single site is reverted to the routing table.
- [x] 3.3 Run the OpenAI e2e attribution test under the fallback provider so
  provider isolation is proven for served models, not just routed ones;
  verified by
  `tests/stages/test_engines_e2e.py::test_openai_session_attributes_agents_to_openai_models`.
- [x] 4.1 `make check` green: ruff, pytest, `openspec validate --strict --all`.
