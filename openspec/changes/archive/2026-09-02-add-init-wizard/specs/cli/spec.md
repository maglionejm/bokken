# cli

## ADDED Requirements

### Requirement: Init wizard

`bokken init` SHALL produce a Brief-schema-valid JSON file from one of three
bundled templates (`saas-retention`, `consumer-app`, `internal-tool`), either
interactively (plain prompts, template defaults pre-filled) or
non-interactively via `--template` and `--out` (placeholders clearly marked
as TODO). It SHALL validate the result against the Brief schema before
writing and SHALL end by printing the exact `bokken new`/`bokken run`
commands that consume the file.

#### Scenario: Guided brief in one sitting

- **WHEN** a user runs `bokken init` and answers the prompts
- **THEN** a validated brief JSON exists on disk and the terminal shows the two commands that start the run

#### Scenario: Non-interactive template

- **WHEN** `bokken init --template consumer-app --out brief.json` runs without a TTY
- **THEN** brief.json is written from the template with TODO placeholders and no prompt is issued
