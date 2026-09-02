# cli

## MODIFIED Requirements

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
