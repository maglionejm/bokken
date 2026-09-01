# report

## ADDED Requirements

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
