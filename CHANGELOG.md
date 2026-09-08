# Changelog

All notable changes to Bokken. Format follows [Keep a Changelog](https://keepachangelog.com/);
versions follow [SemVer](https://semver.org/). Bokken releases strategically —
main may be ahead of the latest PyPI release.

## [Unreleased]

### Added
- Code exploration: when the corpus includes code, Empathize opens with a
  citation-validated map of current capabilities (journaled as
  `current_capability` interpretations) that targets the UI feature tests;
  corpus context headers now declare each source kind's evidence role.
  Adapted from the exploration discipline in build-software-with-style.

### Changed
- Journal invariant: an interpretation is grounded by refs or validated
  corpus citations; with neither it must declare `ungrounded: true`.

### Fixed
- Honesty-core hardening from the full code review (#63): the UI tester's
  destructive-control guard is enforced at `act()` (re-resolved element,
  refused destructive labels and stale indexes), a browser startup failure
  journals an abstention instead of killing the run, report HTML escaping is
  attribute- and script-safe, finalization survives a malformed handoff
  package, a fired transition clears a stale pending gate, and kata budgets
  count executions within the current engine pass.
- Reliability and UX hardening, review batch 2/2 (#64): torn-journal appends
  are refused and partial appends truncated; stalled stages and missing
  engines journal `session.stopped` (reason `error`) before raising; a
  revisited stage regains its full retry budget; founder picks validate 1..n
  with up to 3 re-asks and an explicitly journaled fallback; Twilio `receive`
  returns all fresh inbound messages oldest-first; numeric-string votes map to
  the presented order and an unresolvable winner raises instead of crowning
  option 1; `novelty_floor: 0` is honored; unknown journal type filters raise;
  the library reader skips torn lines; `RunOutcome` carries
  `pending_question_id` as a contract field; interactive `init` and malformed
  `--brief` fail as clean usage errors.

## [1.3.1] — 2026-09-04

### Added
- Claude Desktop one-click bundle: `make mcpb` builds `bokken-<version>.mcpb`
  from a checked-in manifest that wraps `uvx bokken serve`; a drift test pins
  the manifest's tool list to the server's registered tools.

## [1.3.0] — 2026-09-04

### Added
- `bokken init --from-repo PATH`: drafts the brief from the repo's own corpus
  (two disclosed model calls, scratch journal discarded) (#50).
- `bokken pack NAME [--deliverables-only]`: one portable archive per run with
  an honest manifest (verdict, cost, sha256 file index) (#51).
- `bokken handoff --emit claude-code|cursor|codex`: executable adapters over
  the canonical OpenSpec package, with evidence-lookup paths (#52).
- `bokken doctor [--network]`: one-screen environment diagnosis, every
  failing row paired with its fix; `server.json` MCP registry manifest (#53).
- Report themes: builtin `bokken`/`plain` or a JSON theme (brand, label,
  footer) — chrome only, never content; journaled at `new` (#54).
- Demo specimen exercises a bundled mock app in a real browser when the `[ui]`
  extra is installed: per-feature functional tests, screenshots, and an honest
  `broken` finding (#43).
- Demo journals a small, deterministic, clearly-labeled illustrative cost
  profile (~$10 list price) so the cost surfaces show a realistic shape;
  the receipt states $0.00 charged (#43).
- Typed journal reads: `Event.typed_payload`, `payload_as`, `extension`;
  appends are strict while reads stay tolerant (#46).
- `--json` on `version`, `stop`, and `validate`.
- CHANGELOG, CI workflow on pull requests, vendored Chart.js.

### Fixed
- Run-loop predicates: an unrecognized gate policy no longer fails open
  (gateless sessions refused at creation), and loop-back rework is only
  discharged by substantive work in the target stage (#44).
- Attribution derives from the model that actually served the call, so a
  server-side fallback can no longer produce two records disagreeing about
  one contribution (#45).
- README quickstart named a model not in the allowlist (`gpt-5.6-luna`).
- `report.html` is now fully self-contained: Chart.js is vendored and
  inlined instead of loaded from a CDN.
- Stale docs counts (MCP tools, OpenSpec capabilities).

## [1.2.1] — 2026-09-02

- The Anthropic `sidekick` lane routes to `claude-sonnet-5`; model capability
  is a per-model set of lanes enforced at session creation; `bokken costs`
  reports grounding health next to spend (#37, @mpuig).

## [1.2.0] — 2026-09-02

- Budgets count every usage bucket providers report (cached prefix included),
  each priced exactly once (#36, @mpuig).
- Prompt-cache boundaries cover the per-persona loops; two templates
  reordered so their stable prefix actually caches (#38, @mpuig).

## [1.1.1] — 2026-09-02

- Affirmative, journaled consent before interviewing a human (#30, @mpuig).
- Input answers attributed to whoever supplied them; machine answers are
  `simulated` and never human testimony (#31, @mpuig).
- Client-supplied corpus input paths confined at the MCP surface (#32, @mpuig).

## [1.1.0] — 2026-09-02

- `bokken demo`: a complete offline run on the bundled Lanzadera case —
  no API key, ~10 seconds, deterministic (#28).
- `bokken init`: guided brief from three templates (#29).
- Cost framing before `bokken run` and a journal-derived receipt on every
  halt (#33).
- Page gallery with the published demo report and deck (#34).
- OpenAI provider via the `[openai]` extra (#24, @mpuig).

## [1.0.0] — 2026-09-01

- First stable release on PyPI via Trusted Publishing: the full
  Empathize→Define→Ideate→Prototype→Test loop as an executable, event-sourced,
  governed process; CLI + MCP surfaces; dossier, handoff, PPTX + HTML reports;
  validation interviews; insights library; Fusion cost architecture.
