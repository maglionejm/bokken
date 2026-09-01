# validation

## ADDED Requirements

### Requirement: Twilio channel

Behind the optional `interview` extra, `--channel twilio --to <E.164>` SHALL
run the interview over SMS/WhatsApp via Twilio's Messages API using polling
(no webhook server): the first message SHALL request consent and STOP
declines end the interview before any question; answers time out gracefully;
credentials come only from the environment and the raw phone number is never
journaled (the participant label stands in).

#### Scenario: Consent gates the interview

- **WHEN** the participant replies STOP to the consent message
- **THEN** no interview question is sent and nothing is journaled for that participant
