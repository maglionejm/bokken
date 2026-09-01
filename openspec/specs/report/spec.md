# report Specification

## Purpose
The report capability turns a finished run into stakeholder-ready deliverables: a PowerPoint deck and a self-contained HTML page telling the same story — the whole process, every intermediate output, the final outputs, and an appendix of one-line spec summaries pointing at the full handoff files. Both are deterministic renderings of the Journal (no model calls), so they inherit the honesty rules: the Dojo banner, synthetic labels, and validation flags cannot be dropped by a template.

## Requirements

### Requirement: Deterministic journal-only generation

Report generation SHALL be a deterministic function of the Journal and of
files already exported to the session directory. It SHALL make no model
calls, and regenerating SHALL produce identical content up to timestamps.

#### Scenario: No model calls during export

- **WHEN** `export` runs on a completed session
- **THEN** the count of `model.called` events is unchanged afterwards

### Requirement: Two formats, journaled

Export SHALL write `report/report.pptx` (a PowerPoint deck) and
`report/report.html` (a self-contained HTML page telling the same story) in
the session directory, and journal each as `artifact.generated` with kinds
`report_deck` and `report_page` and content hashes. Export SHALL be
idempotent: files are overwritten, but a session that already journaled both
kinds is not re-journaled by finalization.

#### Scenario: Both files exist and are journaled

- **WHEN** export completes
- **THEN** both files exist and `artifact.generated` events with kinds
  `report_deck` and `report_page` are in the Journal

### Requirement: Full process coverage

Both formats SHALL report the entire process and its intermediate outputs —
the brief and inputs, the stage arc including loop-backs, evidence samples
with confidence classes, problem-statement candidates with losers and why
they lost, the concept decision with dissent, prototype artifacts with
assumption mappings, the scored assumption register, facilitation moves, and
research debt — and the final outputs: the recommendation, validation flags,
dossier and handoff pointers, and model usage with an estimated cost labeled
as a list-price estimate.

#### Scenario: Intermediate outputs are present

- **WHEN** a completed dojo session is exported
- **THEN** the HTML contains the problem statement, at least one losing
  option with its `why_lost`, every assumption with its score, and the
  recommendation

### Requirement: Spec appendix

The report SHALL end with an appendix listing each generated handoff spec as
exactly one sentence (taken from the spec's own Purpose text, never
re-generated) followed by the relative path to the full spec file. When the
handoff was refused, the appendix SHALL state the refusal reason instead.

#### Scenario: Specs summarized with pointers

- **WHEN** a session with a generated handoff package is exported
- **THEN** the appendix lists every capability spec with a one-sentence
  summary and its `handoff/openspec/changes/...` path

#### Scenario: Refusal is surfaced

- **WHEN** a killed session is exported
- **THEN** the appendix states that the handoff was refused and why

### Requirement: Honesty carry-over

For dojo sessions both formats SHALL carry the simulated-run banner on the
cover/summary, the synthetic share of the evidence base, and the
requires-real-validation flag on the recommendation.

#### Scenario: Banner survives both formats

- **WHEN** a dojo session is exported
- **THEN** both the deck cover and the HTML header state the run is
  simulated and requires validation with real users

### Requirement: Functional UI review section

When the session journaled a `ui_review` artifact, both report formats SHALL
include a "Functional UI review" section presenting the documented
walkthrough: the screens visited with their observed facts, a per-feature
functional test table (feature, steps taken, verdict, note) when
`ui_feature_tests` artifacts exist, the constructive findings from the
review artifact, and (in the HTML format) the captured screenshots. When no walkthrough ran, the section SHALL be omitted and the
journaled skip reason remains visible in the research-debt listing.

#### Scenario: UI review reaches the report

- **WHEN** a session with an `app_url` input completes and is exported
- **THEN** the HTML report contains a Functional UI review section with the
  walkthrough findings and screenshot images, and the deck contains the
  corresponding slide

#### Scenario: No silent absence

- **WHEN** a session without `app_url` is exported
- **THEN** the reports carry no UI review section and the research-debt
  listing shows the journaled skip

#### Scenario: Feature verdicts reach the report

- **WHEN** a session with journaled feature tests is exported
- **THEN** both formats show each feature with its verdict and the HTML renders the results table

### Requirement: Run anatomy section

Both report formats SHALL open (after the executive summary) with a "How this
run worked" section derived from the Journal: the stage sequence actually
executed, every synthetic persona on the cast with name, role, segment, and
panel, the system agents involved (facilitator, ui-walker, convergence
lenses, skeptic), and the model each routing class ran on with its call
count.

#### Scenario: The cast is visible

- **WHEN** a completed dojo session is exported
- **THEN** both formats list the interview/ideation/test personas by name and
  role and show per-class model usage

### Requirement: Stage sections follow Activity, Process, Output

Every stage section in both formats SHALL present three labeled blocks:
"Agents & activity" (which actors worked, with model-call counts by class),
"Process" (the method applied in that stage), and "Output" (the journaled
results).

#### Scenario: Consistent stage anatomy

- **WHEN** the HTML report renders the Empathize section
- **THEN** it contains the three labeled blocks, and the deck's Empathize
  slide carries the same three-part structure

### Requirement: Graphical HTML

The HTML report SHALL be visually consumable: a scroll progress indicator,
animated stat counters, persona cards, and charts for the assumption
register, the opportunity ranking, and cost by model (horizontal bars, never
pies for more than three categories), with content still readable when
JavaScript is disabled.

#### Scenario: Charts render from journal data

- **WHEN** the HTML report is opened for a session with a scored register and
  an opportunity ranking
- **THEN** it contains chart canvases fed by the journaled scores and a
  no-script fallback listing the same numbers

### Requirement: Concept research section

When `market_research` artifacts exist, both report formats SHALL include a
"Concept research" section presenting the structured findings — competitors
and prior art with overlap, market signals with their source URLs,
regulatory notes, pricing benchmarks, differentiation risks, and open
questions. When research was skipped, the journaled skip remains visible in
the research-debt listing.

#### Scenario: Research reaches the reports

- **WHEN** a session with concept research is exported
- **THEN** the HTML and the deck contain the Concept research section with sourced signals
