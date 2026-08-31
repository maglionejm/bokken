# Tasks: add-dossier-generator

## 1. Dossier model

- [x] 1.1 Implement `DossierModel` (typed graph: insights↔evidence, lineage, IBIS decisions with dissent, persona cards, abstentions, artifact and model traces, transitions, budgets, negative space, labels) built from replay in `src/bokken/dossier/model.py`; verify with fixture journals that every reference resolves within the model
- [x] 1.2 Implement pivotal-moment derivation rules (loop-backs, killed frontrunners, adopted-with-dissent, gate rejections, surviving provocations); verify each rule with a targeted fixture
- [x] 1.3 Implement partial-dossier support (max-stage gating, `status: partial`); verify with an in-flight `ideate` fixture

## 2. Renderers

- [x] 2.1 Implement `JsonRenderer` producing versioned `dossier.json` (Part C + structured A/B); verify against a JSON-schema check and full traversability test
- [x] 2.2 Implement `MarkdownRenderer` producing `dossier.md` (Parts A+B, honesty sections, plain utilitarian English); verify with snapshot tests including receipts (event ids) on every Part A claim
- [x] 2.3 Enforce label rendering structurally (labeled-node renderer API); verify synthetic labeling, confidence propagation, negative space, and the unconditional Dojo banner with tests attempting to configure them away

## 3. Generation flow

- [x] 3.1 Implement `generate(session) -> paths` writing both exports and journaling them as artifacts without any model calls; verify determinism (two runs byte-equal modulo timestamp) and the no-`model.called` scenario
- [x] 3.2 End-to-end: generate dossiers for the offline full-session fixtures from add-stage-engines (Founder and Dojo); verify honesty scenarios and `make check` green
