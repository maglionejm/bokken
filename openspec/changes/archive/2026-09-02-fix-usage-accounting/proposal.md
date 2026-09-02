# Proposal: fix-usage-accounting

## Why

The token meter is a governance control (Blueprint §4: stopping rules
terminate runs and the reason is a Journal event), but it currently cannot see
the largest number on a call. `SessionState.tokens_spent` sums only
`input_tokens` and `output_tokens`, while both provider adapters report the
cached prompt prefix in disjoint `cache_read_tokens` / `cache_write_tokens`
buckets. Measured on this branch, a call with 200,000 billed prompt tokens of
which 195,000 were cache reads registers 5,500 tokens against the budget and
hides 195,000 — so a budget can be deferred indefinitely by cached prompts and
`session.stopped (budget_exhausted)` never fires.

The same usage is also priced two different ways. `cost_rows` charges input at
list price, cache reads at a tenth of input, and output at list price; the
report's per-model usage lines charge only input and output. Neither prices
cache writes, which cost more than plain input on Anthropic. The `costs` verb
and the exported report therefore quote one session at two numbers, and both
understate it.

## What Changes

- Count every billed token bucket in the replayed budget meter, at face value:
  budgets are declared as token counts, so a cached token counts as a token.
  Pricing stays out of the meter.
- Consolidate cost estimation into one `call_cost_usd(model, usage)` function
  covering all four buckets, used by the `costs` verb (CLI and MCP) and by the
  report's model usage lines, so one trace can never be quoted twice.
- Model cache multipliers per provider, read off the model registry's provider
  and list price: Anthropic bills cache reads at 0.1x input and cache writes at
  1.25x input; OpenAI bills cached input at 0.1x input and no separate cache
  write. Neither vendor's multipliers are applied to the other's models.
- Carry cache-read and cache-write tokens on the per-model usage lines and add
  a cache-write column to the cost rows.

Provider-side tool fees (for example a web search request charge) are not
present in either adapter's usage metadata, so they remain absent from the
estimate rather than being guessed at; the estimate stays labeled list-price.

## Capabilities

### New Capabilities

(none)

### Modified Capabilities

- `journal`: replayed budget counters count all billed token buckets.
- `cli`: the cost report prices all four buckets through one pricing function
  with per-provider cache multipliers.
- `report`: the report's model usage estimate is priced by that same function.

## Impact

`src/bokken/journal/replay.py`, `src/bokken/report/context.py`, and their
tests. The `costs`/`cost_report` JSON gains a `cache_write` field per row;
`ModelUsageLine` gains two token fields with defaults, so renderers are
unaffected. Existing sessions re-derive higher `tokens_spent` on replay (the
journal is untouched), which is the point: a run whose budget was silently
overspent now stops.
