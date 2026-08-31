# Tasks: add-stage-engines

## 1. Model ops

- [x] 1.1 Implement `ModelRouter` (routing classes, allowlisted per-session overrides, journaled routing snapshot) in `src/bokken/models/router.py` with a `FakeRouter` for tests; verify class→model resolution and snapshot presence in `session.created`
- [x] 1.2 Integrate the Anthropic SDK: `messages.parse` for structured outputs, `messages.stream` + `get_final_message` for `generation`, adaptive thinking for `cognition`, refusal/`pause_turn`/error handling as typed outcomes; verify with mocked-transport tests per outcome
- [x] 1.3 Implement mandatory `model.called` journaling (class, model, prompt id+hash, request id, usage, status, duration) and budget pre-check with typed budget-exhausted outcome; verify usage→budget replay and refused-dispatch tests
- [x] 1.4 Implement versioned prompt resources with render-hashing in `src/bokken/prompts/`; verify prompt-version visibility across two runs in a test

## 2. Empathize engine

- [x] 2.1 Implement interview-program generation from the brief and adaptive laddering follow-ups (structured-output step schemas); verify follow-up behavior with a scripted fake router
- [x] 2.2 Implement Founder/Dojo interview execution via input port / panel provider with correct confidence classes and research-debt logging; verify the three spec scenarios with fakes

## 3. Define engine

- [x] 3.1 Implement evidence clustering → insights with mandatory refs/ungrounded flags, POV + HMW drafting, and coverage scoring; verify insight-evidence linkage on fixtures
- [x] 3.2 Implement problem-statement selection as an IBIS `decision.recorded` preserving losing framings, with `hmw_reframe` firing on solution-shaped statements; verify both scenarios

## 4. Ideate engine

- [x] 4.1 Implement divergence: quotas (with journaled abstentions), private/public separation, lineage events for create/build/merge/split/park/kill; verify quota enforcement and full lineage reconstruction
- [x] 4.2 Implement novelty monitoring via `extraction` classification with windowed rate + hysteresis, provocation injection through the Kata, and `timebox_pivot`-gated pivot; verify decay→provocation→pivot sequencing with fakes
- [x] 4.3 Implement convergence: frozen-criteria scoring, recorded votes with roles, skeptic-challenge gate, surviving-option decision; verify against panel governance rules

## 5. Prototype engine

- [x] 5.1 Implement assumption-register construction (impact × uncertainty risk classes, riskiest-first) and the journaled fidelity decision; verify riskiest-assumption→artifact-kind mapping scenario
- [x] 5.2 Implement the four MVP artifact generators writing workspace files journaled with assumption refs; verify artifact-without-assumption refusal and path+hash journaling

## 6. Test engine

- [x] 6.1 Implement firewalled evaluation (fresh panel in Dojo; structured read-through in Founder) scoring every register entry supported/contradicted/untested with refs; verify completeness scenario
- [x] 6.2 Implement kill/iterate/proceed recommendation with confidence and `requires_real_validation` propagation, plus `loopback_proposal` on contradictions; verify contradiction→loop-back and simulated-only labeling scenarios

## 7. Integration

- [x] 7.1 End-to-end offline test: full Dojo session `intake → complete` with fake router + scripted panel, gates approved programmatically; verify exit criteria met per stage, all governance events present, `make check` green
- [x] 7.2 Live smoke script (`scripts/smoke_run.py`, not in CI): one tiny Founder-mode run against the real API; verify `model.called` events carry real request ids and usage
