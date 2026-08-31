"""Live smoke run against the real Anthropic API. Not part of CI.

Usage: ANTHROPIC_API_KEY=... uv run python scripts/smoke_run.py
Creates a tiny Dojo session in a temp workspace and runs Empathize only,
then prints the model events so request ids and usage can be inspected.
"""

import os
import sys
import tempfile
from pathlib import Path

from bokken.journal import read_events
from bokken.kata import MVP_MOVES, Kata
from bokken.orchestrator import Runner, create_session
from bokken.stages import anthropic_router_factory, engine_suite

if not os.environ.get("ANTHROPIC_API_KEY"):
    sys.exit("ANTHROPIC_API_KEY is not set")

BRIEF = {
    "problem_space": "helping consultants keep meeting notes actionable",
    "target_segments": ["consultants"],
    "success_criteria": ["a validated problem statement"],
    "risk_tolerance": "low",
}

with tempfile.TemporaryDirectory() as home:
    os.environ["BOKKEN_HOME"] = home
    session_dir = create_session(
        "smoke",
        brief=BRIEF,
        mode="dojo",
        gate_policy=["empathize"],  # halt after the first stage
        budgets={"total_tokens": 200_000},
        config_extra={"panel": {"size": 4, "seed": 1}},
    )
    runner = Runner(
        session_dir,
        engines=engine_suite(anthropic_router_factory()),
        kata_factory=lambda store: Kata(MVP_MOVES, store),
    )
    result = runner.run()
    print(f"halt: {result.halt} at stage {result.stage}\n")
    for event in read_events(session_dir):
        if event.type == "model.called":
            p = event.payload
            print(
                f"{p['prompt_id']}@{p['prompt_version']} {p['model']} "
                f"req={p['request_id']} in={p['usage'].get('input_tokens')} "
                f"out={p['usage'].get('output_tokens')} status={p['status']}"
            )
    print(f"\njournal: {Path(session_dir) / 'journal.jsonl'}")
