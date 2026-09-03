# cli

## MODIFIED Requirements

### Requirement: Init wizard

`bokken init` SHALL produce a Brief-schema-valid JSON file from one of three
bundled templates (`saas-retention`, `consumer-app`, `internal-tool`), either
interactively (plain prompts, template defaults pre-filled) or
non-interactively via `--template` and `--out` (placeholders clearly marked
as TODO). With `--from-repo PATH` it SHALL instead draft the brief from the
repository's own corpus via one extraction-lane and one cognition-lane call
behind the ModelRouter seam, present every drafted field for confirmation
(unless `--yes`), disclose the drafting cost, and discard the scratch
journal. An empty or unreadable corpus SHALL refuse with exit 2 before any
model call. It SHALL validate the result against the Brief schema before
writing and SHALL end by printing the exact `bokken new`/`bokken run`
commands that consume the file.

#### Scenario: Guided brief in one sitting

- **WHEN** a user runs `bokken init` and answers the prompts
- **THEN** a validated brief JSON exists on disk and the terminal shows the two commands that start the run

#### Scenario: Non-interactive template

- **WHEN** `bokken init --template consumer-app --out brief.json` runs without a TTY
- **THEN** brief.json is written from the template with TODO placeholders and no prompt is issued

#### Scenario: Brief drafted from the repo

- **WHEN** `bokken init --from-repo ./myapp --yes` runs against a repo with a readable README
- **THEN** a Brief-valid file is written whose problem space is grounded in the corpus, the repo lands in `inputs.repo`, and the drafting cost is disclosed

#### Scenario: Empty corpus refuses cheaply

- **WHEN** `--from-repo` points at a directory with nothing ingestible
- **THEN** the command exits 2 before any model call and writes nothing
