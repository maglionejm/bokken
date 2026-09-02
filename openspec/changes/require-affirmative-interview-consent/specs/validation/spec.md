# validation

## ADDED Requirements

### Requirement: Affirmative, journaled consent before any interview question

No interview question SHALL reach a real human before that human has
affirmatively opted in. The Channel port SHALL report a consent outcome of
`granted | declined | no_response | ambiguous` together with the basis in
words; only `granted` SHALL allow the interview to proceed, and silence, a
timed-out answer window, an ambiguous reply, and an explicit decline SHALL all
end the run. The consent request SHALL be sent once and answered once — no
reminder and no retry pestering the participant.

The engine SHALL journal `interview.consent_requested` before the channel
reaches the participant and `interview.consent_resolved` (with `refs` to the
request, the outcome, and the basis) before any interview question may be sent,
both carrying the participant label and the channel and neither carrying the
raw phone number. A consent exchange SHALL never be journaled as evidence.
The refusal reason surfaced to the operator SHALL distinguish an explicit
decline from never having heard back. Channels SHALL have no journal
knowledge; they only ask and report what came back.

#### Scenario: Silence is not consent

- **WHEN** the participant never replies and the answer window times out
- **THEN** the outcome is `no_response`, no interview question is sent, no model call is made, and the journal holds the request and its `no_response` resolution

#### Scenario: An ambiguous reply is not consent

- **WHEN** the participant replies "who is this?"
- **THEN** the outcome is `ambiguous`, no interview question is sent, and the journal records that outcome against the participant label

#### Scenario: A decline is distinguishable from silence

- **WHEN** one participant declines and another never replies
- **THEN** the operator is told which of the two happened, and both are journaled with their own outcome

#### Scenario: The founder-relayed channel is not exempt

- **WHEN** the interview runs over the terminal channel and the operator does not confirm that the participant consented
- **THEN** the outcome is `no_response` and no question is relayed

## MODIFIED Requirements

### Requirement: Twilio channel

Behind the optional `interview` extra, `--channel twilio --to <E.164>` SHALL
run the interview over SMS/WhatsApp via Twilio's Messages API using polling
(no webhook server): the first message SHALL request consent, and only a bare
affirmative reply SHALL start the interview — a decline, a hedge, an unrelated
reply, and no reply at all SHALL each end it before any question is sent;
answers time out gracefully; credentials come only from the environment and
the raw phone number is never journaled (the participant label stands in).

#### Scenario: Consent gates the interview

- **WHEN** the participant replies STOP to the consent message
- **THEN** no interview question is sent and the journal records the contact and its `declined` outcome against the participant label

#### Scenario: A silent number is not interviewed

- **WHEN** the number never replies to the consent message
- **THEN** the only outbound message is that consent request and the run ends with `no_response`
