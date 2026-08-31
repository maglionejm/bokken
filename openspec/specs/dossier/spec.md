# dossier Specification

## Purpose
The dossier capability turns a session's Journal into the Session Dossier: a defensible, honest account of what was produced and how — outcomes (Part A), process narrative with receipts (Part B), and the full machine-readable evidence graph (Part C) — generated on demand from the ledger alone.

## Requirements

### Requirement: Journal is the sole input

The Dossier generator SHALL derive all content exclusively from the session's journal (and artifact files referenced by journaled path+hash); it SHALL NOT invoke models, panels, or any source outside the session workspace. Generating a dossier SHALL NOT append events to the journal other than an `artifact.generated` record for the dossier files themselves.

#### Scenario: Deterministic regeneration

- **WHEN** the dossier is generated twice from the same journal
- **THEN** both outputs are identical apart from the generation timestamp

#### Scenario: No model calls during generation

- **WHEN** a dossier is generated
- **THEN** no `model.called` events are added to the journal

### Requirement: Part A — Outcomes

Part A SHALL present, concisely: the selected problem statement (with its decision reference), the advanced concept(s), the prototype artifacts with their assumption register and per-assumption scores, test results with the kill/iterate/proceed recommendation and its confidence, decisions with owners and dates, and the recommended next loop. Every claim in Part A SHALL carry a ledger reference (event id) resolvable in Part C.

#### Scenario: Outcome claims have receipts

- **WHEN** Part A states the recommendation for a completed session
- **THEN** the statement references the `decision.recorded` event id, and that id resolves in Part C

#### Scenario: In-flight session yields a partial Part A

- **WHEN** a dossier is generated for a session currently in `ideate`
- **THEN** Part A is labeled partial, reports progress through `define`, and omits unreached sections rather than fabricating them

### Requirement: Part B — Process narrative

Part B SHALL tell the run as a readable story: the arc through the stages with ledger references, the pivotal moments, the options seriously considered and why the losers lost, the dissent registered and how it was handled, where the facilitation (Kata) intervened and to what effect, and any loop-backs with the evidence that fired them. It SHALL be written so a stakeholder who was absent can find "did you consider X?" answered with references.

#### Scenario: Losers and dissent are narrated

- **WHEN** the journal contains a decision with two rejected options and one recorded reservation
- **THEN** Part B names the rejected options with their losing reasons and reports the reservation and its handling

#### Scenario: Loop-backs appear with their triggers

- **WHEN** the journal contains a `test → define` loop-back
- **THEN** Part B narrates it citing the contradicting evidence references

### Requirement: Part C — Evidence graph

Part C SHALL be a machine-readable JSON document containing: every insight with its evidence links (and ungrounded flags), the complete idea lineage graph, every decision's IBIS record including dissent, every persona's provenance card (casting parameters, grounding scope) and abstentions, artifact traces (path, hash, assumption links), model traces (per `model.called`: class, model, prompt version, usage), and the stage-transition history. The JSON structure SHALL be versioned (`dossier_schema_version`) and treated as a public contract.

#### Scenario: Graph is fully traversable

- **WHEN** Part C is loaded by a consumer
- **THEN** every reference (evidence id, option id, decision id, persona id) resolves to a node within the document

#### Scenario: Persona provenance is complete

- **WHEN** a Dojo session's Part C is generated
- **THEN** each persona that contributed has a provenance card and all its abstentions are listed

### Requirement: Honesty rules

The Dossier SHALL enforce: (1) synthetic contributions labeled `synthetic` at the line/record level wherever they appear in Parts A/B/C — simulated research is never presented as user insight; (2) confidence-class propagation — any conclusion resting on `assumed` or `simulated` evidence displays its inherited class and the `requires_real_validation` flag; (3) negative space — a dedicated section listing what was not done (methods skipped, stages compressed, quorums not met, research debt outstanding); and (4) Dojo banner — dossiers from autonomous runs open with a banner stating the run was simulated, evidence-bounded, and requires real-user validation for the decisions above the flag threshold.

#### Scenario: Synthetic insight is labeled in Part A

- **WHEN** Part A includes a finding grounded only in persona evidence
- **THEN** the finding is labeled synthetic inline and flagged `requires_real_validation`

#### Scenario: Negative space is stated

- **WHEN** a run skipped a method and carries three open research-debt items
- **THEN** the dossier's negative-space section lists the skipped method and all three items

#### Scenario: Dojo banner is unconditional

- **WHEN** any dossier is generated for a Dojo-mode session
- **THEN** it opens with the simulated-panel banner, and no configuration can remove it

### Requirement: Exports

The generator SHALL write `dossier/dossier.md` (Parts A and B, with the honesty sections) and `dossier/dossier.json` (Part C plus structured A/B data) into the session workspace, journaling both as artifacts. Output SHALL be plain, utilitarian English without emojis or decorative Unicode.

#### Scenario: Both exports are produced and journaled

- **WHEN** `dossier` generation is requested
- **THEN** both files exist in the session workspace and each has an `artifact.generated` event with its content hash
