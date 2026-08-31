# Tasks: fix-input-aware-rework

## 1. Fixes

- [x] 1.1 Bump `empathize/interview_program` to v2 with input-kind calibration and pass `inputs_available` from the brief; verify the dojo e2e still grounds evidence and the prompt version is journaled
- [x] 1.2 Add `events_since_transition` to replay and force one engine pass after a loop-back in the runner; verify with `test_loopback_forces_engine_rework_before_fast_forward`
- [x] 1.3 Dossier `decision_for` picks the latest matching decision; verify existing dossier tests stay green
- [x] 1.4 `make check` green (129 tests) and the live vatios session resumes past `define` after loop-back rework
