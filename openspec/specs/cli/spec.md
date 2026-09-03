# cli Specification

## Purpose
The CLI is Bokken's terminal surface: barista-style lifecycle verbs over named, durable, resumable sessions, exposing the full DT loop — creation, running, gates, loop-backs, ledger, and dossier — as a thin adapter over the shared core with disciplined human and machine output.

## Requirements

### Requirement: Session lifecycle verbs

The CLI SHALL provide: `bokken new <name>` (create; interactive brief intake by default, `--brief <file>` for non-interactive; options for `--mode founder|dojo`, `--gates`, `--budget`, typed inputs — `--repo <path>` for an app repository to explore, `--app-url <url>` for a running instance of the product to walk through, `--metrics <path>` for business/performance data, `--discussion <path>` for interview transcripts and needs statements, `--doc <path>` for other documents (each repeatable) — and routing overrides), `bokken run <name>` (resume-and-continue; halts at pending gate, pending human input, stop, or completion), `bokken step <name>` (at most one stage), `bokken stop <name>`, `bokken status <name>`, and `bokken list`. All verbs SHALL address sessions by name and operate purely through the core (no CLI-side state).

#### Scenario: New then run then interrupt then run

- **WHEN** a user creates `mars-lander`, runs it, kills the process mid-stage, and runs it again
- **THEN** the second run resumes from the journal without repeated work and without any CLI-side recovery steps

#### Scenario: Non-interactive creation

- **WHEN** `bokken new mars-lander --brief brief.md --mode dojo` is invoked with a valid brief file
- **THEN** the session is created without prompting, and `bokken status mars-lander` reports stage `intake`, mode `dojo`, and the default Dojo gate policy

#### Scenario: Status shows what blocks progress

- **WHEN** a Dojo run has halted at a gate
- **THEN** `bokken status` names the pending gate, the stage boundary it guards, and the command to resolve it

### Requirement: Gate and loop-back verbs

The CLI SHALL provide `bokken gate <name> approve|reject [--reason <text>]` resolving the pending gate (rejection requires a reason) and `bokken back <name> <stage> --reason <text>` requesting a human-initiated loop-back to a legal earlier stage. Both SHALL act by appending the corresponding journal events through the core; illegal targets (no pending gate; illegal loop-back edge) SHALL fail with a specific error and exit code 2.

#### Scenario: Approve resumes the run

- **WHEN** `bokken gate mars-lander approve` is invoked with a gate pending and then `bokken run mars-lander`
- **THEN** the gate resolution is journaled and the run proceeds past the boundary

#### Scenario: Illegal loop-back is refused

- **WHEN** `bokken back mars-lander prototype` is invoked from stage `define`
- **THEN** the command fails with exit code 2 naming the legal loop-back edges

### Requirement: Journal access

`bokken journal <name>` SHALL print ledger events with filters `--type <type-or-family>`, `--stage <stage>`, `--actor <kind>`, `--since <seq|timestamp>`, `--limit <n>`, and `--follow` (stream new events until interrupted). Default output SHALL be a compact human-readable line per event; `--json` SHALL emit one canonical JSON event per line (JSONL).

#### Scenario: Filtered tail

- **WHEN** `bokken journal mars-lander --type option --stage ideate --follow` runs during divergence
- **THEN** only `option.*` events from `ideate` stream, one per line, as they are appended

### Requirement: Dossier verb

`bokken dossier <name>` SHALL generate the dossier via the core and print the paths of `dossier.md` and `dossier.json`; `--json` SHALL print a JSON object with the paths and dossier status (`complete|partial`). Generation for in-flight sessions SHALL be permitted and labeled partial per the dossier capability.

#### Scenario: Dossier from the terminal

- **WHEN** `bokken dossier mars-lander --json` is invoked mid-run
- **THEN** the output JSON contains both file paths and `"status": "partial"`

### Requirement: Founder-mode interaction contract

During interactive runs the CLI SHALL render stage openings, questions, syntheses, and Kata move outputs as plain conversational prompts; user answers SHALL be captured through the core's input port (journaled as human evidence/decisions per the schema). Interactive prompts SHALL always display which stage the session is in and SHALL support saving-and-exiting cleanly (Ctrl-C leaves the session resumable, never corrupt).

#### Scenario: Ctrl-C is safe

- **WHEN** the user interrupts an interactive interview mid-question
- **THEN** the process exits cleanly, no partial event is written, and `bokken run` resumes at the pending question

### Requirement: Output discipline and exit codes

All output SHALL be plain utilitarian English without emojis or decorative Unicode. Every read verb SHALL support `--json` emitting stable, documented shapes. Exit codes SHALL be: `0` success (including clean halts at gates/stops), `1` unexpected error, `2` invalid usage or refused operation (unknown session, illegal transition, validation failure). Errors SHALL be written to stderr; machine output to stdout only.

#### Scenario: Machine consumption is clean

- **WHEN** `bokken status mars-lander --json` succeeds
- **THEN** stdout contains exactly one JSON document, stderr is empty, and the exit code is 0

#### Scenario: Unknown session

- **WHEN** any verb references a session name that does not exist
- **THEN** the command exits 2 with a stderr message naming the workspace searched

### Requirement: Handoff verb and run finalization

The CLI SHALL provide `bokken handoff <name>` generating the OpenSpec handoff package via the core and printing the package directory (with `--json` returning the directory, the change id, and the capability list). When `bokken run` halts `completed`, the CLI SHALL finalize the session automatically — Dossier first, then handoff — skipping outputs that already exist and skipping the handoff for `kill` recommendations, reporting in the run output what was generated or skipped.

#### Scenario: Handoff from the terminal

- **WHEN** `bokken handoff mars-lander --json` runs on a completed session with a `proceed` recommendation
- **THEN** stdout is a single JSON document with the package path and generated capabilities, and the package exists on disk

#### Scenario: Completion finalizes automatically

- **WHEN** `bokken run mars-lander` returns `completed` for the first time
- **THEN** the Dossier and the handoff package are generated without further commands, and a second `run` does not regenerate them

### Requirement: Export verb

`bokken export <name>` SHALL regenerate both report files via the core and
print their paths; `--json` SHALL print a JSON object with both paths. It
SHALL exit `2` when the session does not exist or has no events to report.

#### Scenario: Export from the terminal

- **WHEN** `bokken export mars-lander --json` is invoked on a completed
  session
- **THEN** stdout is one JSON document with the `pptx` and `html` paths and
  the exit code is 0

### Requirement: Web research authorization flag

`bokken new --allow-web-research` SHALL set `allow_web_research: true` on
the brief; without it the flag defaults to false. The setting SHALL be
visible in the journaled config/brief snapshot.

#### Scenario: Flag lands in the brief

- **WHEN** `bokken new x --brief b.json --allow-web-research` is invoked
- **THEN** the journaled brief carries `allow_web_research: true`

### Requirement: Costs verb

`bokken costs <name>` SHALL print a deterministic cost report derived from
replayed `model.called` events: one row per stage x prompt_id x routing
class with calls, input, output, and cache-read tokens, a list-price
estimate labeled as such, per-model subtotals with cache hit-rate, and the
run total. The report SHALL also carry grounding health folded from the same
journal: persona turns, how many of them abstained, and how many of those
abstentions the grounding backstop forced because a citation did not resolve
to a corpus span, reported as both a count and a share of persona turns. That
share SHALL be distinguishable from honest research gaps, so a delegated lane
made cheaper cannot degrade citation quality invisibly. `--json` SHALL emit the
same data as one JSON document.

#### Scenario: Costs from the terminal

- **WHEN** `bokken costs mars-lander --json` runs on a completed session
- **THEN** stdout is one JSON document whose totals equal the sum of the
  journaled usage priced at the list table

#### Scenario: Backstop-forced abstentions are visible next to spend

- **WHEN** a run's persona turns include answers whose citations did not resolve to a corpus span
- **THEN** the costs report counts those turns separately from honest abstentions and reports their share of persona turns

#### Scenario: One trace, one number

- **WHEN** a session containing a cache-heavy call is priced by the cost
  report and by the exported report's model usage lines
- **THEN** both quote the same total for that session

### Requirement: Validate verb

`bokken validate <name> [--participant NAME] [--channel terminal]` SHALL
build (or reuse) the validation guide and run one agentic interview over the
selected channel, journaling exchanges and rescoring; `--guide-only` SHALL
stop after producing the guide. Exit code 2 when the session has no research
debt and no untested assumptions.

#### Scenario: Guide only

- **WHEN** `bokken validate mars-lander --guide-only` runs on a completed session
- **THEN** a `validation_guide` artifact exists and no interview is started

### Requirement: Library verb

`bokken library [--product KEY]` SHALL list the accumulated learnings
(session, product, verdict, non-untested assumption scores); `--json` SHALL
emit the raw records.

#### Scenario: Learnings from the terminal

- **WHEN** `bokken library --json` runs after a finalized session
- **THEN** stdout is one JSON document containing that session's record

### Requirement: Demo verb

`bokken demo [name]` SHALL create and run a complete dojo session offline —
no API key, no network calls — against a bundled scripted provider and
corpus whose citations resolve, finishing with finalization (dossier, PPTX,
HTML) and printing the report paths plus a receipt that states the user was
charged $0.00. The scripted calls SHALL journal a deterministic,
deliberately lean illustrative usage profile (single-digit-dollars list
price, drawn per routing class from a fixed table) so the cost surfaces in
both report formats and `bokken costs` show a realistic live-run shape;
`bokken costs` on a demo session SHALL label the usage as illustrative and
restate that nothing was charged. The fixtures SHALL include a static mock of
the fictional product declared as a `file://` app_url: when the `[ui]` extra
is available the demo SHALL run the real browser walkthrough and per-feature
functional tests against it (journaled `observed` evidence, screenshots,
per-feature verdicts rendered in both report formats); when it is not, the
demo SHALL keep the honest journaled skip. The output SHALL be deterministic
across runs on the same machine apart from session name, timestamps, and
browser-measured artifacts (screenshots, load timings), and SHALL carry every
honesty marker of a real dojo run
(simulated banner, journaled walkthrough skip when applicable,
requires-real-validation).

#### Scenario: One command to a full report

- **WHEN** `bokken demo` runs on a machine with no ANTHROPIC_API_KEY
- **THEN** it completes with a full journal, resolvable citations, both report files on disk, and a receipt stating the user was charged $0.00

#### Scenario: Costs are illustrated small and labeled

- **WHEN** the demo session is priced by `bokken costs` or rendered in the reports
- **THEN** the journaled usage totals a small single-digit-to-low-teens dollar figure at list prices and the costs verb labels it as illustrative with $0.00 charged

#### Scenario: Deterministic showcase

- **WHEN** `bokken demo a` and `bokken demo b` run
- **THEN** their reports differ only in session name, timestamps, and browser-measured artifacts

#### Scenario: The specimen shows the feature tests

- **WHEN** `bokken demo` runs with the `[ui]` extra installed
- **THEN** the journal carries per-feature `observed` evidence from the mock app and both report formats render the feature verdicts, including one honest `broken` finding

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

### Requirement: Run cost framing and receipt

`bokken run` SHALL print, before entering the loop, the session's token
guardrail and the typical full-run cost range; and on halt SHALL print a
receipt computed from journaled model calls — session-to-date list-price
cost in USD and total calls — with a pointer to `bokken costs` for the
per-stage breakdown. In `--as-json` mode the receipt fields SHALL appear in
the result payload.

#### Scenario: Receipt on halt

- **WHEN** a run halts for any reason (gate, budget, completion, stop)
- **THEN** the terminal shows the session-to-date cost and call count derived from the journal

#### Scenario: Framing before spend

- **WHEN** `bokken run` starts on a fresh session
- **THEN** the guardrail and typical cost range are shown before the first model call

### Requirement: Pack verb

`bokken pack NAME` SHALL produce a single zip archive containing a
`manifest.json` (bokken version, session facts, verdict, list-price cost,
packed-at timestamp, and a per-file index with sizes and sha256 digests)
plus the session's deliverables: self-contained HTML report, deck, dossier,
and handoff tree. By default the journal, evidence graph, and artifacts are
included; `--deliverables-only` SHALL omit them and the manifest SHALL state
the omission and its verifiability consequence. Packing SHALL never mutate
the session, and an unfinalized session SHALL be refused with exit 2 and a
pointer to `bokken export`.

#### Scenario: The run as one portable object

- **WHEN** `bokken pack retention` runs on a finalized session
- **THEN** `retention.bokken.zip` exists with a manifest whose file index digests match the packed files, and the report inside opens offline

#### Scenario: External sharing is honest about omissions

- **WHEN** `bokken pack retention --deliverables-only` runs
- **THEN** the bundle omits journal, dossier.json, and artifacts, and the manifest states that claims are not independently verifiable from the bundle alone

#### Scenario: Unfinalized sessions are refused

- **WHEN** `bokken pack` targets a session with no report
- **THEN** it exits 2 telling the operator to run `bokken export` first
