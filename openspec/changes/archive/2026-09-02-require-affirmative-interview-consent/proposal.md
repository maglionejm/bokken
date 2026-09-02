# Proposal: require-affirmative-interview-consent

## Why

Live defect in the validation interview path (Blueprint §4, no silent
self-escalation). `TwilioChannel.open` treated everything except `STOP | NO |
BAJA` as consent — including the empty string `receive()` returns when its
answer window times out. A real phone number that never replied, or replied
"who is this?", was read as having opted in and the engine went on to send it
interview questions. Nothing about the outbound contact was journaled either:
only the participant's answers became `evidence.captured`, so reaching a real
human who never consented left no trace in the ledger at all — against
"everything is an event" and against the rule that exists precisely to stop a
run contacting real humans unaccountably.

## What Changes

- Consent becomes explicitly affirmative on every channel: `Channel.open`
  returns a `Consent` verdict (`granted | declined | no_response | ambiguous`)
  plus the basis in words, and only `granted` may be followed by a question.
  Silence, a timeout, a hedge, and an explicit decline all refuse the
  interview, and the reason surfaced to the operator distinguishes a decline
  from never hearing back.
- The consent request is sent once, answered once: no reminder, no retry.
- The terminal channel gets the same treatment: it prints the consent script
  and requires the operator to confirm, at the terminal, that the participant
  consented in their own words; an unattended terminal is `no_response`.
- New `interview.*` journal events: `interview.consent_requested` lands before
  the channel reaches the human, `interview.consent_resolved` (refs the
  request) lands before any interview question may be sent. Both carry the
  participant label and the channel; the raw phone number still never enters
  the ledger, and a refused contact is never journaled as evidence.
- The channel abstraction stays journal-free; the engine, which holds the
  store, owns the journaling.

## Capabilities

### New Capabilities

(none)

### Modified Capabilities

- `journal`: taxonomy v1 gains the `interview.*` family for consent to contact
  a real human.
- `validation`: affirmative consent, journaled, before any interview question.

## Impact

`src/bokken/interview/channels.py`, `src/bokken/interview/engine.py`,
`src/bokken/journal/schema.py`, the `validate` CLI command's error path,
`docs/events.md`, and `tests/interview/test_validation.py`.
