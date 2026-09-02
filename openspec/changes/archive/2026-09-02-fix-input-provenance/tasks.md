# Tasks

- [x] 1.1 Add `Answer` (text + supplying `Actor`, with confidence-class and
  source derivation) to the orchestrator and make `InputPort.ask` return it;
  verified by the orchestrator runner tests.
- [x] 1.2 Stamp the human founder in `TerminalInputPort`; verified by
  `tests/cli/test_cli.py::test_terminal_port_answers_are_human_attributed`.
- [x] 1.3 Carry the submitting client's handshake actor through the MCP input
  mailbox and stamp it in `submit_input` from `Context`; verified by
  `tests/mcp/test_mcp_server.py::test_submitted_input_is_attributed_to_the_client_not_the_founder`.
- [x] 2.1 Journal Empathize interview answers, the Test read-through, and
  Ideate's founder contributions and convergence decision with the supplier's
  actor and a supplier-derived confidence class; verified by the founder-mode
  e2e run (human path) and the MCP attribution test (agent path).
- [x] 2.2 Confirm propagation into `requires_real_validation` and the Dossier's
  synthetic labeling; verified by
  `tests/mcp/test_mcp_server.py::test_agent_supplied_evidence_is_labeled_synthetic_in_the_dossier`
  and the decision-flag assertions in the attribution test.
- [x] 3.1 Correct `docs/mcp.md` on what the input mailbox confers; verified by
  review against the implemented behavior and `make check`.
