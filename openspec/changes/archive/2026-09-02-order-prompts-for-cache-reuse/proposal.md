# Proposal: order-prompts-for-cache-reuse

## Why

The `models` spec already promises that a corpus read by twelve interview turns
is "written once and read from cache thereafter" (Blueprint §5, parallel prompt
caches). It was not: `CACHE_SPLIT` appeared in exactly one template
(`sidekick/context_query`), and the two per-persona templates put the varying
material *above* the stable material - `empathize/persona_turn` named the
persona before the corpus, `empathize/outcome_scores` named the persona before
the shared outcome list - so successive calls in those loops had no common
prefix to cache at all.

Ordering is the whole cost lever here. A cache read is about a tenth of fresh
input while a cache write is about 1.25x, so a prefix written once and read five
times is a large win and a prefix that varies per call is strictly worse than no
marker: it pays the write premium every time and never reads. Any template whose
stable material sits below its varying material is unfixable by markup alone.

## What Changes

- Reorder `empathize/persona_turn` and `empathize/outcome_scores` so the shared
  material (corpus; outcome list) leads and the per-call material (persona,
  question) follows, preserving the in-character, cite-the-line-span, and
  abstain-honestly framing those prompts carry.
- Declare a cache split on the three loops whose shared prefix is large enough
  to be cached by the routed models: `empathize/persona_turn` (one corpus, every
  persona), `ideate/converge` (one option set, three lenses), and
  `test/evaluate` (one artifact, every assumption). Bump each changed template's
  version.
- Leave `empathize/outcome_scores` reordered but unmarked, and record why: its
  shared prefix is 5-10 outcome statements, below the smallest cacheable prefix
  any routed model accepts, so a marker there could only ever be inert.
- Memoize sidekick retrieval per (question, corpus) in `RouterTurnGenerator`.
  Every persona on a panel asks the identical question over the identical
  corpus; re-invoking the sidekick paid for the same retrieval N times and, since
  the model need not answer identically, handed each persona turn a *different*
  corpus prefix - N cache writes and no reads.
- Raise `DELEGATE_THRESHOLD_CHARS` from 20k to 120k. Delegation's break-even
  moves once the undelegated corpus is itself cacheable on the frontier lane: at
  20k chars the sidekick's retrieval output, priced as frontier output tokens on
  every question, costs several times more than simply reading the corpus back
  from cache.

## Capabilities

### New Capabilities

(none)

### Modified Capabilities

- `models`: prompt templates must order shared material before per-call material
  so a declared cache split has a prefix to cache, and delegation must not
  destabilize that prefix.

## Impact

`src/bokken/models/prompts.py`, `src/bokken/stages/persona_gen.py`, and their
tests. No journal, replay, router, or report change: `split_cache_marker` and
the marker-stripped prompt hash already existed, so the wire payload for an
unmarked prompt is unchanged and every `model.called` record keeps naming the
prompt version and hash actually used. The four bumped template versions mean
new runs journal `v4`/`v2`/`v3`/`v3` while existing journals keep their own.
