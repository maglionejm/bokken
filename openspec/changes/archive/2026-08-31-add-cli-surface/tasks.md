# Tasks: add-cli-surface

## 1. Skeleton and presentation

- [x] 1.1 Implement the Typer root app, verb modules, presenter (Rich/JSON switch), exit-code mapper, and stdout/stderr discipline in `src/bokken/cli/`; verify with `CliRunner` tests for the machine-consumption scenario (single JSON doc, empty stderr, exit 0) and unknown-session (exit 2)
- [x] 1.2 Wire `bokken --version` and `--help` metadata; verify help output contains all spec verbs

## 2. Lifecycle verbs

- [x] 2.1 Implement `new` (interactive intake via `TerminalInputPort` + `--brief` non-interactive path with all options), `list`, `status`; verify non-interactive creation and status-shows-blocker scenarios with a fake-engine core
- [x] 2.2 Implement `run`, `step`, `stop` including halt semantics (gate/input/stop/completion all exit 0 with a state line); verify new→run→kill→run resumability in a subprocess test
- [x] 2.3 Implement Ctrl-C safety for interactive prompts (no partial event, resumable); verify with a scripted interrupt test

## 3. Gates, loop-backs, journal, dossier

- [x] 3.1 Implement `gate approve|reject --reason` and `back <stage> --reason`; verify approve-resumes and illegal-loop-back (exit 2, names legal edges) scenarios
- [x] 3.2 Implement `journal` with all filters, `--limit`, `--follow`, and `--json` JSONL output; verify filtered-tail scenario with a live appender
- [x] 3.3 Implement `dossier` (paths + `--json` with status); verify partial-status scenario mid-run

## 4. Integration

- [x] 4.1 End-to-end CLI test: drive a full offline Dojo session (new → run → gate approvals → dossier) purely through the CLI with the fake router; verify journal completeness and `make check` green
