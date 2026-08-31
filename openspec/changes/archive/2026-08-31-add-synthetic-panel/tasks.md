# Tasks: add-synthetic-panel

## 1. Personas and casting

- [x] 1.1 Implement `Persona`, role agents, and the seeded casting sampler over segment axes with OCEAN jitter in `src/bokken/panel/casting.py`; verify with tests for segment coverage, mandatory roles, and manifest reproducibility from (brief, seed)
- [x] 1.2 Journal the casting manifest before any panel content; verify with a test that manifest events precede all persona evidence events

## 2. Corpus and grounding

- [x] 2.1 Implement corpus ingestion (local files → source id + SHA-256 + line-addressable spans) in `src/bokken/panel/corpus.py`; verify with tests for id stability and span resolution
- [x] 2.2 Implement the `PersonaTurnGenerator` protocol with `GroundedAnswer`/`Abstention` types and the post-hoc citation validator (invalid citation → abstention `citation_invalid`); verify with fake generators for grounded, ungrounded, and invalid-citation cases
- [x] 2.3 Journal grounded answers as `evidence.captured` (`simulated`, citations) and abstentions as `evidence.abstained`; verify research debt is enumerable from replayed state

## 3. Governance

- [x] 3.1 Implement the contamination firewall (manifest disjointness check, journaled verification, abort-on-overlap) in `src/bokken/panel/firewall.py`; verify with tests for fresh-panel pass and overlap refusal
- [x] 3.2 Implement anti-sycophancy rendering (preference stripping from persona-visible material) and the criteria-freeze guard; verify with tests that preferred-answer markers never appear in rendered persona prompts and post-freeze mutations are refused
- [x] 3.3 Implement the protected skeptic quota blocking convergence until a challenge exists; verify with a convergence attempt lacking skeptic input
- [x] 3.4 Implement `requires_real_validation` propagation for decisions resting on simulated/assumed evidence and reject any config that disables synthetic labeling; verify both with tests

## 4. Integration

- [x] 4.1 Wire the panel as a Dojo `InputPort`/interview provider consumable by orchestrator fakes; end-to-end test: cast → interview → abstentions → firewall-checked evaluation with scripted generators, `make check` green
