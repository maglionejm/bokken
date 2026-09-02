# Tasks: require-affirmative-interview-consent

## 1. Affirmative consent on the channel port

- [x] 1.1 `Channel.open` returns a `Consent` verdict (`granted | declined |
  no_response | ambiguous` + basis) instead of `None`, and classifies replies
  so that only a bare affirmative grants; verified by the Twilio cases where
  silence, a hedge, a question back, and a decline all fail to grant and only
  the consent message is ever sent.
- [x] 1.2 Terminal channel requires an operator confirmation of consent and
  reports an unattended terminal as `no_response`; verified by the terminal
  channel cases (yes/si/no/empty/hedge and EOF).

## 2. Journal the contact

- [x] 2.1 Add `interview.consent_requested` / `interview.consent_resolved` to
  taxonomy v1, the latter requiring refs to the request; verified by the
  consent-boundary tests asserting the linked pair.
- [x] 2.2 `run_validation_interview` journals the request before the channel
  reaches the human and the outcome before any question, then refuses unless
  consent was granted; verified by the no-response, ambiguous, and declined
  cases (no question sent, no model call, no evidence) and by the happy path
  asserting `requested.seq < resolved.seq < first evidence.seq`.
- [x] 2.3 `bokken validate` surfaces the refusal reason plainly, distinguishing
  a decline from no response; verified by the distinct `REFUSAL` reasons test.

## 3. Documentation and definition of done

- [x] 3.1 Document the `interview.*` family in `docs/events.md`; verified by
  `openspec validate --strict --all` and `make check`.
