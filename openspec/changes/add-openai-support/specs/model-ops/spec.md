# Model provider support

## ADDED Requirements

### Requirement: OpenAI can serve routed model calls
The system SHALL support OpenAI models through the existing model router seam,
including plain text and Pydantic structured-output calls.

#### Scenario: OpenAI structured call
- **WHEN** a session routes a call to an OpenAI model with a Pydantic schema
- **THEN** the provider returns validated data and the router appends one
  `model.called` event with usage, model, request id, and status

#### Scenario: OpenAI provider failure
- **WHEN** the OpenAI SDK or network raises an exception
- **THEN** the router returns an error outcome and journals the failed call

### Requirement: Provider selection is explicit and optional
The system SHALL allow a session to select `anthropic` or `openai`, SHALL reject
unsupported provider/model configuration, and SHALL not import the OpenAI SDK
until an OpenAI call is dispatched.

#### Scenario: Offline installation
- **WHEN** Bokken is installed without the OpenAI optional extra
- **THEN** import, fake-provider tests, and Anthropic sessions continue to work

#### Scenario: OpenAI session
- **WHEN** a session is created with provider `openai`
- **THEN** its default routing uses supported OpenAI models and calls use the
  `OPENAI_API_KEY` credential
