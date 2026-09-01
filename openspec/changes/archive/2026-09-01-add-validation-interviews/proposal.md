# Proposal: add-validation-interviews

## Why

Every dojo run ends flagged `requires_real_validation`, and the research
debt dies as a list nobody executes. The best-funded market players
(Listen Labs, Outset) converge on the same shape: an AI *moderates*
interviews with real humans; synthetic panels only pre-test. Bokken already
produces the guide (debt + untested assumptions) — it needs the interviewer.

## What Changes

- New `validation` capability: `bokken validate <name>` builds a structured
  interview guide from the session's research debt and untested assumptions
  (journaled `validation_guide` artifact), then an agentic interviewer
  (research class) conducts a real interview turn by turn over a Channel
  port — asking, laddering, concluding — journaling every exchange as
  `reported` evidence with `actor.kind: human` for the participant.
- After each interview a challenge-class call rescores the untested
  assumptions against the real evidence (`assumption.scored` with reported
  refs); reports gain a "Real validation" section showing synthetic-vs-real
  register deltas.
- Channel port ships with a zero-dependency TerminalChannel; sessions accept
  appends after completion (validation is a first-class post-run phase).

## Capabilities

### New Capabilities

- `validation`: guide, agentic interviewer, rescoring, honesty rules.

### Modified Capabilities

- `cli`: validate verb.

## Impact

`src/bokken/interview/*` (new), prompts, CLI, report renderers, tests.
