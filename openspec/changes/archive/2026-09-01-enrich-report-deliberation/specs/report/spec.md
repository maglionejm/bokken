# report

## ADDED Requirements

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

## MODIFIED Requirements

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
