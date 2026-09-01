# Proposal: add-twilio-channel

## Why

The founder wants validation interviews to reach real participants where
they are - SMS/WhatsApp - without standing up server infrastructure.

## What Changes

- TwilioChannel behind the `interview` extra: polling Messages API (no
  webhooks), consent-first, STOP honored, graceful answer timeout,
  credentials from env, phone numbers never journaled.
- CLI: `bokken validate --channel twilio --to <number>`.

## Capabilities

### New Capabilities

(none)

### Modified Capabilities

- `validation`: Twilio channel requirement.

## Impact

interview/channels.py, CLI, pyproject extra, channel test.
