# Tasks

- [x] Route the Anthropic `sidekick` lane to `claude-sonnet-5`; verified by a routing-default test and by the sidekick delegation test asserting the journaled model.
- [x] Replace the boolean frontier flag with a per-model set of servable routing classes taken from the journal taxonomy, and refuse undeclared classes at session creation; verified by a test that rejects `claude-haiku-4-5` on every lane but `extraction` and asserts both default tables route only declared lanes.
- [x] Keep OpenAI lane economics intact and assert the sidekick default is cheaper than every judgment lane on both providers; verified by routing tests.
- [x] Separate citation-invalid abstentions from honest persona-turn abstentions and report them in `bokken costs` and MCP `cost_report`; verified by a panel unit test over a scripted paraphrase plus the end-to-end costs CLI test.
- [x] Update `docs/agents.md` and `docs/operating.md`; verified with `make check`.
