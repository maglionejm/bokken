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

The per-model usage lines SHALL carry cache-read and cache-write tokens
alongside input and output, and SHALL be priced by the same shared pricing
function the `costs` verb uses, so the report and the cost report agree on any
one session.

#### Scenario: Intermediate outputs are present

- **WHEN** a completed dojo session is exported
- **THEN** the HTML contains the problem statement, at least one losing
  option with its `why_lost`, every assumption with its score, and the
  recommendation

#### Scenario: The report's estimate includes cached tokens

- **WHEN** a session whose spend is mostly a cached prompt prefix is exported
- **THEN** the report's cost estimate prices those cache reads and cache
  writes and equals the `costs` verb total for the same session

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
walkthrough: the screens visited with their observed facts, per-feature
functional test cards - verdict, finding, the executed step log, and that
feature's end-state screenshot - when `ui_feature_tests` artifacts exist, the constructive findings from the
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

### Requirement: Deliberation is visible

Both report formats SHALL present the agents' deliberation from the
Journal: each convergence lens vote with its position (and verdict, effort,
and first slice when present), the skeptic challenge verbatim, Kata moves
executed and suppressed with triggers, and every decision's criteria and
dissent.

#### Scenario: Lens votes reach the reader

- **WHEN** a completed dojo session is exported
- **THEN** the HTML shows a deliberation section with one entry per lens
  vote and the skeptic challenge, and the deck carries the same content

### Requirement: Self-contained visuals

The HTML report SHALL render its screenshots as embedded data URIs so the
file is portable and images never break outside the session directory.

#### Scenario: Report file travels alone

- **WHEN** report.html is copied out of the session directory and opened
- **THEN** all screenshots still render

### Requirement: Action orientation

Stage sections SHALL open with quantified stat chips (counts, scores) and
the report SHALL close with a "Next actions" list derived from journaled
material: broken feature findings, the recommendation's constructive next
step, and the top open research debt.

#### Scenario: The founder knows what to do next

- **WHEN** a session with broken feature verdicts and an iterate
  recommendation is exported
- **THEN** the report contains a next-actions list citing those findings

### Requirement: Opportunity Solution Tree view

The HTML report SHALL include an Opportunity Solution Tree chapter derived
from the journal graph — the framed outcome at the root, the Ulwick-ranked
opportunities beneath it, the advanced solution under each, and its
assumption tests with their scores — rendered as a collapsible tree; the
section states honestly when no ranking was journaled.

#### Scenario: The tree reads from the journal

- **WHEN** a session with an opportunity ranking is exported
- **THEN** the HTML shows outcome, opportunities, solution, and scored assumption tests as nested, collapsible nodes

### Requirement: Report themes

Report generation SHALL accept a theme - a builtin name (`bokken`, `plain`)
or a JSON file with brand color, dark variant, brand label, and footer -
that changes deliverable chrome and never content: the HTML report's accent
palette, brand label, and footer are themed via a CSS custom-property
override, and the deck carries the themed label and footer. Theme colors
SHALL be validated as `#rrggbb` and an unknown theme SHALL refuse with exit
2. A theme chosen at session creation SHALL be journaled in the config
snapshot and honored by every later export, so regenerated reports are
stable; an explicit `--theme` on export overrides for that export only.

#### Scenario: A consultant white-labels the deliverable

- **WHEN** `bokken export retention --theme acme.json` runs with a valid theme file
- **THEN** the HTML report carries the theme's accent color, brand label, and footer, and the run's content is byte-identical apart from that chrome

#### Scenario: Themes cannot lie

- **WHEN** a theme file carries a non-hex color or an unknown builtin name is passed
- **THEN** the export refuses with exit 2 before writing anything
