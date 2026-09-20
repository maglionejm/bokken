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
run total. The report SHALL also carry a three-line functional rollup
aggregated from those same rows by prompt-id prefix — exploration
(understanding the product: `explore/`, `sidekick/`, the feature inventory
and UI walkthrough calls), research (learning from people: persona,
interview, follow-up and outcome calls, `research/`, `validate/`), and
synthesis (everything else) — whose three subtotals sum to the run total.
The report SHALL also carry grounding health folded from the same
journal: persona turns, how many of them abstained, and how many of those
abstentions the grounding backstop forced because a citation did not resolve
to a corpus span, reported as both a count and a share of persona turns. That
share SHALL be distinguishable from honest research gaps, so a delegated lane
made cheaper cannot degrade citation quality invisibly. `--json` SHALL emit the
same data as one JSON document, and the MCP `cost_report` payload SHALL carry
the same rollup.

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

#### Scenario: The functional rollup sums to the total

- **WHEN** `bokken costs <name> --json` runs on a session with exploration, persona, and synthesis calls
- **THEN** the payload carries exploration/research/synthesis subtotals that sum to the run total

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
charged $0.00. The demo marker SHALL be journaled in the session config, and
every later wiring of the session — resume via the run/step verbs,
finalization, and handoff regeneration, over CLI or MCP — SHALL select the
same offline scripted provider and never a real provider, so an interrupted
demo stays offline across resumes and the $0.00 receipt stays true. The
scripted calls SHALL journal a deterministic,
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

#### Scenario: Interrupted demo resumes offline

- **WHEN** a demo session is stopped mid-run and resumed with `bokken run` on a machine with no provider keys
- **THEN** the resumed run completes on the offline scripted provider, finalization included, and `bokken costs` still reports illustrative usage with $0.00 charged

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

### Requirement: Doctor verb

`bokken doctor` SHALL report, offline by default, the environment facts a
run depends on - version, workspace path and writability, provider key
presence (values never printed), each optional extra with the consequence
of its absence, browser availability when the ui extra is present, Twilio
credential completeness when the interview extra is present, and the MCP
input-root configuration - pairing every failing check with the exact fix
command. `--network` SHALL add provider reachability probes; `--json` SHALL
emit the same checks machine-readably with an overall `ok` flag.

#### Scenario: A failing environment explains itself

- **WHEN** `bokken doctor` runs with no API key and no extras
- **THEN** each missing item shows its consequence and its fix command, and secrets are never echoed

#### Scenario: Machine-readable diagnosis

- **WHEN** `bokken doctor --json` runs
- **THEN** stdout is one JSON document with per-check name/ok/detail/fix and an overall ok flag

### Requirement: Opportunities verb

`bokken opportunities <name>` SHALL print a deterministic segment × outcome
opportunity matrix derived purely from the replayed journal — no model calls —
addressing the session by name through the core. Rows SHALL be the segments
present on the session's personas and columns SHALL be the desired outcomes;
each cell SHALL show the mean Ulwick opportunity score over the personas of that
segment who scored that outcome, together with that cell's sample size (the
number of such personas). The opportunity score SHALL be computed by the same
definition the report uses, so the verb and the report agree for any one
session. A cell whose sample size is below two SHALL be flagged as
low-confidence in the output. For a dojo session the output SHALL state that the
matrix is simulated and requires validation with real users. `--json` SHALL emit
the same data as one JSON document with a stable shape (segments, outcomes, and
per-cell `score`, sample size `n`, and low-confidence flag). A session with no
scored outcomes SHALL exit 2 with a message naming what is missing, and an
unknown session SHALL exit 2 per the CLI's output discipline.

#### Scenario: The matrix is computed with per-cell sample sizes

- **WHEN** `bokken opportunities mars-lander --json` runs on a completed session
  whose personas span two segments and scored the desired outcomes
- **THEN** stdout is one JSON document whose cells are keyed by
  `(segment, outcome)`, each carrying the mean opportunity score over that
  segment's personas for that outcome and the count `n` of personas behind it,
  and the totals reconcile with the report's derivation for the same session

#### Scenario: A thin cell is flagged low-confidence

- **WHEN** only one persona in a segment scored a given outcome and
  `bokken opportunities mars-lander` is run
- **THEN** that cell shows its score and sample size `n=1` and is flagged
  low-confidence in both the human matrix and the `--json` output

#### Scenario: Dojo framing carries onto the matrix

- **WHEN** `bokken opportunities mars-lander` is run on a dojo session
- **THEN** the output states the matrix is simulated and requires validation
  with real users

#### Scenario: No scored outcomes is refused

- **WHEN** `bokken opportunities mars-lander` is run on a session that never
  scored desired outcomes
- **THEN** the command exits 2 with a message naming that no outcome scores were
  journaled, and writes no matrix
### Requirement: Diff verb

`bokken diff <old> <new>` SHALL compare two finalized runs of the *same product* and report what moved between them, by derivation only — it SHALL build the shared read model for each session (the dossier model built from the journal alone) and diff it, making no model calls, no journal writes, and no mutation of either session. The report SHALL cover four axes: (1) **opportunity re-ranking** — Ulwick outcomes present in both runs matched by statement, each with its `<old>` and `<new>` opportunity score and band and their deltas, plus outcomes added in `<new>` and outcomes dropped from `<old>`; (2) **assumptions that flipped status** — assumptions matched by statement whose score changed, reporting the `<old>` and `<new>` score (drawn from `supported | contradicted | untested`), plus assumptions added and dropped; (3) **current capabilities added / removed / changed** — the code-exploration `current_capability` insights matched by statement; and (4) **verdict change** — the recommendation (`kill | iterate | proceed`) of each run and whether it changed.

Every reported row SHALL label which run it came from (`old`, `new`, or `both`) and SHALL carry the confidence class of the material it summarizes, copied unchanged from the two read models — the diff SHALL NOT re-derive, re-ground, or relabel anything, so material grounded only in `simulated` or `assumed` evidence stays labelled synthetic in the diff and real testimony reads as such. The verb SHALL refuse with exit code `2`, writing a specific message to stderr and no diff to stdout, when either session is not finalized, or when the two sessions are not the same product — product identity being the library product key (`inputs.repo`, or the brief `problem_space` when no repo is set). The default output SHALL be a plain utilitarian terminal table (no emojis, no decorative Unicode); `--json` SHALL emit exactly one JSON document conforming to the documented `DiffResult` shape, carrying the same per-row run provenance and confidence classes as the table. A combined cross-run HTML report is out of scope for this requirement.

#### Scenario: What moved between two runs of one product

- **WHEN** `bokken diff retention-v1 retention-v2 --json` is invoked on two finalized sessions built from the same repository, where the second run re-ranked an opportunity, flipped an assumption from `untested` to `supported`, added a current capability, and changed the verdict from `iterate` to `proceed`
- **THEN** stdout is exactly one `DiffResult` JSON document (stderr empty, exit code 0) whose opportunity section shows the re-ranked outcome with both scores and the delta, whose assumptions section shows the `untested -> supported` flip, whose capabilities section lists the added capability, and whose verdict section reports `iterate -> proceed`, with every row labelled by run of origin and carrying its confidence class

#### Scenario: Different products are refused

- **WHEN** `bokken diff app-alpha app-beta` is invoked on two finalized sessions whose product keys differ (different `inputs.repo`, or different `problem_space` when neither sets a repo)
- **THEN** the command exits `2` with a stderr message naming that the two sessions are not the same product, and writes no diff to stdout

#### Scenario: An unfinalized session is refused

- **WHEN** `bokken diff done-run in-flight-run` is invoked where `in-flight-run` has not reached the `complete` stage
- **THEN** the command exits `2` with a stderr message naming which session is not finalized and pointing to how to finalize it, and writes no diff to stdout
### Requirement: Estimate verb

`bokken estimate <brief.json>` SHALL predict a run's token usage and
list-price cost **before** any session is created, by derivation only - no
`ModelRouter` call, no provider SDK, no network, and no journal written. It
SHALL accept `--panel-size` (default 6, matching `bokken new`), `--provider`,
and `--model`, and SHALL price on the **served** model that the brief's
provider/model routing would resolve to (via the same routing resolution a
created session uses), reusing the single pricing function so the estimate and
a later `bokken costs` receipt speak one pricing language. The estimate SHALL
be built from the per-routing-class token profile and the run's executed
prompt set, scaling the research lane with panel size (more personas -> more
per-persona research-lane calls). Output SHALL be a **low-high USD range**
(never a single false-precision number) plus a **per-functional-lane
breakdown** - exploration / research / synthesis, using the same lane
vocabulary as the costs functional rollup - each lane reporting its estimated
calls, tokens, and cost, and the three lane costs SHALL sum to the estimate's
point figure. The surface SHALL be labeled a **modeled estimate** and SHALL
state its assumptions - the panel size assumed and that the token profile is
an illustrative modeled profile, not a measurement of this brief - and SHALL
NOT present the figure as a guaranteed or actual cost. `--json` SHALL emit one
`EstimateResult` JSON document on stdout carrying the range, the per-lane
breakdown, the assumptions, and the modeled-estimate caveat; a missing or
schema-invalid brief file SHALL exit `2` with a stderr message and write no
model call.

#### Scenario: Modeled estimate with a range and lane breakdown

- **WHEN** `bokken estimate brief.json --panel-size 6 --json` is invoked with a
  valid brief
- **THEN** stdout is one `EstimateResult` JSON document carrying a low-high USD
  range whose low does not exceed its high, an exploration/research/synthesis
  lane breakdown whose lane costs sum to the point estimate, a stated
  assumption that the panel size is 6 and the profile is a modeled estimate,
  and no session is created and no model is called

#### Scenario: The estimate scales with panel size

- **WHEN** `bokken estimate brief.json --panel-size 10` and
  `bokken estimate brief.json --panel-size 4` are run against the same brief
- **THEN** the panel-size-10 estimate's cost and research-lane call count are
  strictly greater than the panel-size-4 estimate's, because more personas add
  per-persona research-lane calls

#### Scenario: Honest about being an estimate, never a guarantee

- **WHEN** `bokken estimate brief.json` prints its human-readable output
- **THEN** the output labels the figure a modeled estimate drawn from an
  illustrative profile, states it is not a measurement or a guarantee, and
  points to `bokken costs` for the actual list price once a run exists

#### Scenario: A missing brief is refused before any work

- **WHEN** `bokken estimate does-not-exist.json` is invoked
- **THEN** the command exits `2` with a stderr message naming the unreadable
  brief and no session, journal, or model call is produced
### Requirement: Backlog verb

`bokken backlog <name>` SHALL print a deterministic, replay-derived validation
to-do list built from the journal alone with no model call. It SHALL rank the
session's untested and contradicted assumptions by impact x uncertainty
(reading the journaled `impact` and `uncertainty` on each assumption and the
`score` from its latest scoring), highest first, and SHALL fold every open
research-debt abstention in as a backlog item. Supported assumptions SHALL NOT
appear. The default output SHALL be a plain terminal table with one row per
item carrying at least rank, kind (`assumption` or `research_debt`), impact,
uncertainty, confidence class, source/provenance, and the statement or open
question. Every item SHALL carry its `confidence_class` and its session
provenance, and a simulated-only backlog SHALL keep the simulated framing
(restating the dojo banner and that the run still requires real validation) so
it is never read as validated fact. The report SHALL include a single
"what would flip the verdict" line derived from the register versus the test
recommendation: since the recommendation is a challenge-class judgement over
the register rather than a mechanical cutoff, that line SHALL state the
register counts (supported / contradicted / untested) and the gap plainly —
how many untested items remain to resolve and that any contradicted item is a
standing kill-or-iterate signal — rather than asserting an invented threshold.
`--json` SHALL emit exactly one `BacklogResult`-shaped JSON document with the
ranked items, the register counts, the flip-the-verdict text, and the honesty
flags; `--format csv` and `--format markdown` SHALL emit an issue-tracker
checklist of the same ranked items. Exit codes SHALL follow the CLI output
discipline: `2` for an unknown session, `0` otherwise (including an empty
backlog).

#### Scenario: Ranked backlog with CSV and markdown export

- **WHEN** `bokken backlog mars-lander` runs on a completed dojo session whose
  register holds untested and contradicted assumptions plus open research debt,
  and then the same command is run with `--format csv` and with
  `--format markdown`
- **THEN** the terminal table lists the assumption and research-debt items
  ranked by impact x uncertainty with each item's confidence class and source,
  shows the "what would flip the verdict" line with the register counts, and
  the `--format csv` and `--format markdown` runs emit the same ranked items as
  an issue-tracker checklist

#### Scenario: Empty backlog when nothing is untested

- **WHEN** `bokken backlog mars-lander --json` runs on a session whose
  assumptions are all supported and which has no open research debt
- **THEN** stdout is one `BacklogResult` JSON document with an empty item list,
  the register counts, and a flip-the-verdict line stating there is nothing
  left to test, and the exit code is `0`

#### Scenario: A simulated-only backlog keeps the simulated framing

- **WHEN** `bokken backlog mars-lander --json` runs on a dojo session whose
  assumption scores came only from the synthetic panel
- **THEN** every item carries `confidence_class` `simulated`, and the payload
  keeps the simulated framing (dojo banner and requires-real-validation), so
  the backlog is not presented as validated fact
