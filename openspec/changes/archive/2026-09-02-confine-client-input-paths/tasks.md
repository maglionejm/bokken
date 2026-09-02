# Tasks

- [x] Add input-root resolution (`BOKKEN_HOME`/cwd, `BOKKEN_INPUT_ROOTS` override) and path confinement for a brief's `inputs` block; verified with `tests/panel/test_inputs.py::test_confinement_refuses_traversal_symlinks_and_outside_paths`.
- [x] Confine client-supplied paths in `create_session_tool` and journal the authorized roots in the config snapshot; verified with `tests/mcp/test_mcp_server.py::test_client_input_paths_are_confined_to_the_workspace` and `::test_operator_can_widen_the_input_root`.
- [x] Apply the text-suffix allowlist to explicitly named files and enforce per-file and per-set size caps for every caller; verified with `tests/panel/test_inputs.py::test_named_file_outside_the_text_allowlist_is_reported_not_read`, `::test_named_directory_walk_is_bounded_by_the_corpus_cap`, and `::test_single_oversized_file_is_reported_not_read`.
- [x] Re-check journaled roots during ingestion and journal every refused or skipped input as `evidence.input_rejected`; verified with `tests/panel/test_inputs.py::test_confined_run_skips_inputs_that_escape_the_root` and `::test_rejected_input_lands_in_the_journal`.
- [x] Keep the operator (CLI) surface unconfined; verified with `tests/cli/test_cli.py::test_operator_supplied_absolute_input_path_is_not_confined`.
- [x] Document the boundary and the override in `docs/mcp.md`, `docs/operating.md`, and `docs/events.md`; verified with `make check`.
