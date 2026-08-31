# report

## ADDED Requirements

### Requirement: Functional UI review section

When the session journaled a `ui_review` artifact, both report formats SHALL
include a "Functional UI review" section presenting the documented
walkthrough: the screens visited with their observed facts, the constructive
findings from the review artifact, and (in the HTML format) the captured
screenshots. When no walkthrough ran, the section SHALL be omitted and the
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
