# Recipes

Cookbook for common changes. Each recipe lists the exact files to touch **in
order** and the test that must ride in the **same commit**. These follow the
seams described in [codebase-map.md](codebase-map.md); when a step names a
symbol, grep it to find the current line.

## (a) Add a prompt

1. `src/bokken/models/prompts.py` — add a `PROMPTS` entry keyed by
   `prompt_id -> (version, template)`. Put `CACHE_SPLIT` after the stable
   corpus, before the per-call tail.
2. `src/bokken/stages/schemas.py` — add the Pydantic model for the structured
   output you expect back.
3. `tests/stages/fake_provider.py` — add a `_dispatch` branch for the new
   `prompt_id` in `ScriptedProvider` so tests can exercise it offline.
4. `src/bokken/demo/provider.py` — add the matching `_dispatch` branch so
   `bokken demo` stays deterministic and offline.
5. **Test (same commit):** a router or stage test that calls
   `render_prompt(<prompt_id>, ...)` and asserts the parsed schema comes back.

`make check` must be green; the test rides in the same commit.

## (b) Add an event type

1. `src/bokken/journal/schema.py` — add the type to `TAXONOMY`. If it carries
   *optional* keys, add them to `EXTENSION_KEYS`; do **not** add typed fields
   to an existing type (that re-hashes old records — see gotchas).
2. `src/bokken/journal/replay.py` — add the `_apply` handler that folds the new
   event into `SessionState`.
3. **Test (same commit):** a schema/forward-compat test — write the event,
   replay it, assert the projected state; assert a tolerant read ignores an
   unknown extension key.

`make check` must be green; the test rides in the same commit.

## (c) Add a CLI verb

1. `src/bokken/cli/app.py` — add the verb, decorated `@guarded`.
2. `src/bokken/contract.py` — add or reuse the result shape (a `BaseModel` with
   a `kind` literal) so `--json` and MCP return the same structure.
3. `src/bokken/mcp/server.py` — mirror the verb as an `@mcp.tool` returning the
   same contract shape; keep client paths confined.
4. **Test (same commit):** a `--json`-parity test asserting the CLI `--json`
   output and the MCP tool result serialize to the same contract shape.

`make check` must be green; the test rides in the same commit.

## (d) Add a stage or exit criterion

1. `src/bokken/stages/` — implement the stage engine (or the new gate logic);
   `run(ctx)` returns via `structured()`, and `None` means budget → stop.
2. `src/bokken/orchestrator/machine.py` — wire `FORWARD`/`LOOPBACKS` and extend
   `can_exit` with the per-stage exit criterion.
3. `src/bokken/orchestrator/runner.py` — add the loop predicate; fail **closed**
   on anything unrecognized.
4. **Test (same commit):** a mode-parity test proving the criterion behaves
   identically in founder and dojo mode (dojo answers stay `simulated`).

`make check` must be green; the test rides in the same commit.

## (e) Add a report / deliverable section

1. `src/bokken/report/context.py` — derive the section's data from the journal
   (no model call at render time); price via `call_cost_usd` if cost is shown.
2. `src/bokken/report/page.py` — render it in the HTML, escaping through `_e`
   (and `</`→`<\/` if it lands in a `<script>`).
3. `src/bokken/report/deck.py` — add the matching PPTX slide.
4. **Test (same commit):** a render test asserting the section appears **and**
   that honesty flags (`simulated`/`assumed`) render on any synthetic content.

`make check` must be green; the test rides in the same commit.
