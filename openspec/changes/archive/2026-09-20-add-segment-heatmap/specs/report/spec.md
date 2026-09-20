## ADDED Requirements

### Requirement: Segment opportunity heatmap

When the journal carries scored desired outcomes, both report formats SHALL
include an "Underserved by segment" section presenting the ODI/Ulwick core — a
segment × outcome opportunity matrix. It SHALL be a deterministic derivation of
the Journal with no model calls: the report context SHALL group the replayed
per-persona `outcome_score` interpretations by `(segment, outcome)` and compute,
per cell, the mean Ulwick opportunity score and the sample size (the number of
that segment's personas who scored that outcome), using the same opportunity
scoring the `opportunities` verb uses so the two agree for any one session. The
HTML SHALL render the matrix as a heatmap with segments as rows and desired
outcomes as columns; every cell SHALL show both its opportunity score and its
sample size, and cells whose sample size is below two SHALL be visibly flagged
as low-confidence. The HTML SHALL remain readable with JavaScript disabled (a
no-script fallback listing the same cell numbers). The deck SHALL carry the
matching slide. For a dojo session this section SHALL carry the simulated-run
framing along with the rest of the report and never drop it. A session with no
scored outcomes SHALL omit the section.

#### Scenario: The heatmap is derived with per-cell sample sizes

- **WHEN** a completed session whose personas span multiple segments and scored
  the desired outcomes is exported
- **THEN** the HTML contains the "Underserved by segment" section as a segment ×
  outcome heatmap in which each cell shows its mean opportunity score and the
  sample size of personas behind it, the deck carries the matching slide, and
  the count of `model.called` events is unchanged by export

#### Scenario: A low-confidence cell is flagged in the report

- **WHEN** a segment × outcome cell is backed by a single persona and the
  session is exported
- **THEN** that cell shows its score and sample size and is visibly flagged as
  low-confidence in the HTML heatmap (and its no-script fallback), and the deck
  slide flags the same cell

#### Scenario: Dojo framing survives the heatmap section

- **WHEN** a dojo session with scored outcomes is exported
- **THEN** the "Underserved by segment" section is present alongside the
  simulated-run banner and neither the banner nor the requires-real-validation
  framing is dropped

#### Scenario: No scored outcomes, no section

- **WHEN** a session that never scored desired outcomes is exported
- **THEN** neither the HTML nor the deck contains an "Underserved by segment"
  section
