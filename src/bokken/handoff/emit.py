"""Target-specific handoff adapters: the OpenSpec package stays canonical,
adapters are thin renderings a coding agent can execute directly.

No model calls - everything is assembled from the already-generated package.
"""

from __future__ import annotations

import json
from pathlib import Path

TARGETS = ("claude-code", "cursor", "codex")


class EmitError(RuntimeError):
    pass


def _change_dir(handoff_root: Path) -> Path:
    candidates = sorted((handoff_root / "openspec" / "changes").glob("*/"))
    if not candidates:
        raise EmitError("no handoff package found - run `bokken handoff <name>` first")
    return candidates[0]


def _handoff_md(session: str, change_id: str, change_dir: Path, trace: dict) -> str:
    tasks = (change_dir / "tasks.md").read_text(encoding="utf-8")
    proposal = (change_dir / "proposal.md").read_text(encoding="utf-8")
    why = proposal.split("## Why", 1)[-1].split("##", 1)[0].strip()
    specs = sorted((change_dir / "specs").glob("*/spec.md"))
    spec_lines = "\n".join(
        f"- `openspec/changes/{change_id}/specs/{s.parent.name}/spec.md`" for s in specs
    )
    exclusions = trace.get("exclusions", [])
    exclusion_block = (
        "\n".join(f"- Do NOT build on: {e['statement']}" for e in exclusions)
        or "(none - no assumption was contradicted)"
    )
    return f"""# Execute this handoff: {change_id}

You are implementing the validated MVP from Bokken run `{session}`.
This file is an execution prompt; the OpenSpec package next to it is the
source of truth.

## Why this exists

{why}

## How to execute

1. Copy `openspec/changes/{change_id}/` into the target repository's
   `openspec/changes/` (run `openspec init` there first if needed).
2. Run `openspec validate --strict` and fix nothing by hand - if validation
   fails, the package is damaged; regenerate it.
3. Implement in the order `tasks.md` sequences the work. Each requirement's
   scenarios are the acceptance tests; write them as tests first.
4. Ship the first slice of each capability before starting the second - the
   slices were sized to de-risk the contradicted and untested assumptions.
5. Archive the change when the target repo's checks are green.

## What you must not build

{exclusion_block}

## Specifications

{spec_lines}

## Evidence lookups

Requirement -> assumption ids: `traceability.json` (next to this file's
parent package). Assumption ids -> evidence: `../../../dossier/dossier.json`.
The append-only ledger is `../../../journal.jsonl`. If a requirement seems
wrong, check its evidence before overriding it - and record why.

## Task plan (verbatim from the package)

{tasks}
"""


_CLAUDE_COMMAND = """---
description: Implement the Bokken handoff package in this repository
---

Read HANDOFF.md and the OpenSpec change under openspec/changes/ that came
with it. Follow "How to execute" exactly: validate the specs, implement in
tasks.md order treating every scenario as an acceptance test, ship first
slices first, and never build on anything listed under "What you must not
build". Report progress against tasks.md checkboxes.
"""

_CURSOR_RULES = """---
description: Bokken handoff execution rules
alwaysApply: true
---

This repository contains a Bokken handoff package (HANDOFF.md + an OpenSpec
change). When implementing: follow tasks.md sequencing, treat spec scenarios
as acceptance tests, ship first slices before second slices, and refuse to
build anything listed under "What you must not build" in HANDOFF.md.
"""

_CODEX_AGENTS = """# Agent instructions: Bokken handoff

This repo carries a Bokken handoff package. HANDOFF.md is the execution
prompt; the OpenSpec change under openspec/changes/ is the source of truth.
Implement in tasks.md order, scenarios are acceptance tests, first slices
ship first, and the "What you must not build" list is binding.
"""


def emit_adapters(session_dir: Path, targets: list[str]) -> list[Path]:
    """Render adapter files under handoff/adapters/<target>/; returns paths."""
    unknown = [t for t in targets if t not in TARGETS]
    if unknown:
        raise EmitError(f"unknown emit target(s) {unknown}; pick from {list(TARGETS)}")
    handoff_root = session_dir / "handoff"
    change_dir = _change_dir(handoff_root)
    trace = json.loads((handoff_root / "traceability.json").read_text(encoding="utf-8"))
    handoff_md = _handoff_md(session_dir.name, change_dir.name, change_dir, trace)
    written: list[Path] = []

    def write(rel: str, content: str) -> None:
        path = handoff_root / "adapters" / rel
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content, encoding="utf-8")
        written.append(path)

    for target in targets:
        write(f"{target}/HANDOFF.md", handoff_md)
        if target == "claude-code":
            write(f"{target}/.claude/commands/build-mvp.md", _CLAUDE_COMMAND)
        elif target == "cursor":
            write(f"{target}/.cursor/rules/bokken-handoff.mdc", _CURSOR_RULES)
        elif target == "codex":
            write(f"{target}/AGENTS.md", _CODEX_AGENTS)
    return written
