# Design: add-cli-surface

## Context

See proposal.md. Constraints: the CLI is a thin adapter — all behavior lives in the core (orchestrator/journal/dossier); the MCP surface (next change) must reuse the exact same core calls; output discipline comes from the project conventions (no emojis, utilitarian, English).

## Goals / Non-Goals

**Goals:**

- Zero business logic in `src/bokken/cli/` — verbs map 1:1 to core calls; anything a verb needs that the core lacks is added to the core first.
- Scriptability as a first-class citizen (`--json`, stdout/stderr split, stable exit codes) since the CLI is also how CI and power users will drive Dojo runs.

**Non-Goals:**

- Shell completion, TUI dashboards, `watch`-style rich live views (Rich `--follow` line output is enough for MVP).
- Config files for CLI defaults (flags + env `BOKKEN_HOME` only; revisit if flag fatigue appears).

## Decisions

1. **Typer app with one module per verb group** (`session.py`, `gates.py`, `journal.py`, `dossier.py`) mounted on a root app — keeps each verb testable via Typer's `CliRunner`. Alternative: argparse — Typer is already a dependency and gives typed options and help for free.
2. **`--json` implemented as a rendering switch, not separate code paths** — every verb produces a typed result object from the core; a single presenter renders it as Rich text or JSON. Prevents drift between human and machine output.
3. **Interactive intake/interview via a `TerminalInputPort`** implementing the orchestrator's input-port protocol with Rich prompts; Ctrl-C safety comes from the core's append-before-effect discipline (the port never half-writes events).
4. **Exit-code mapping in one place** — core typed errors → `2`, unexpected exceptions → `1` with a short stderr message (full traceback only under `BOKKEN_DEBUG=1`).
5. **`bokken run` for Dojo sessions runs in the foreground to the next halt** — no daemonization in MVP; long runs are resumable by construction, and backgrounding is the shell's job (`&`, tmux).

## Risks / Trade-offs

- [Interactive UX quality is the product's first impression] → snapshot-test rendered prompts; keep stage banners minimal (stage name + goal line, per Kata `stage_contract`).
- [JSON shapes become a de-facto API before MCP lands] → shapes are documented in the spec and reused as the MCP tool result shapes — one contract, two surfaces.

## Open Questions

- None blocking.
