# Tasks

- [x] 1.1 Extract the loop's decisions out of `_loop` into named functions
  (`halt_result`, `approved_gate_target`, `gate_required`, `rework_pending`,
  `is_substantive_work`, `stall_detail`, `_stop_on_budget`); verified by
  `tests/orchestrator/test_loop_predicates.py` exercising each one directly
  and by the unchanged runner tests
  (`uv run pytest tests/orchestrator`).
- [x] 2.1 Validate gate policies instead of interpreting them: add
  `GatePolicyError`, `normalize_gate_policy`, `default_gate_policy`, and
  `resolve_gate_policy`; refuse at creation (including through `config_extra`)
  and at the start of every run; verified by
  `test_unrecognized_gate_policy_is_refused_loudly`,
  `test_typoed_gate_policy_is_refused_before_the_session_exists`,
  `test_typoed_gate_policy_in_config_extra_is_refused_too`, and
  `test_typoed_gate_policy_never_yields_a_gateless_run`.
- [x] 2.2 Confirm a valid policy still gates exactly its stages and that an
  undeclared policy resolves from the mode; verified by
  `test_stage_list_gate_policy_still_gates_exactly_its_stages` and
  `test_dojo_journal_that_declares_no_policy_still_gates`.
- [x] 2.3 Confirm the CLI refusal contract needs no boundary change; verified
  by `bokken new <name> --mode dojo --gates stage_boundary` exiting 2 with the
  legal forms named on stderr.
- [x] 3.1 Require substantive work by the target stage's engine to discharge a
  loop-back's rework; verified by
  `test_loopback_with_only_a_refused_call_does_not_fast_forward`,
  `test_rework_pending_needs_work_by_the_target_stage`, and
  `test_substantive_work_classification`.
- [x] 3.2 Confirm the requirement does not deadlock a legitimate loop-back;
  verified by `test_loopback_rework_is_satisfied_by_real_work` and the existing
  `test_loopback_forces_engine_rework_before_fast_forward`.
- [x] 4.1 Read and fold the journal once per loop iteration and drop the
  post-engine replay of a journal known to be unchanged; verified by the full
  suite passing unchanged (`uv run pytest`), the behavior being observationally
  identical.
- [x] 5.1 `make check` green (ruff, pytest, `openspec validate --strict --all`).
