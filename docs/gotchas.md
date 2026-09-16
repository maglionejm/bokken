# Gotchas

A ledger of hard-won lessons. Each entry is a failure mode we actually hit:
**SYMPTOM** (what you'll see) → **RULE** (what to do) → evidence (the PR that
paid for the lesson). Read this before touching the seams it names.

## Journal integrity

**Torn journal crashes reads.** A process killed mid-append leaves a partial
line; naive readers crash and one bad session takes down the whole listing.
→ Refuse to append onto a torn tail (truncate the partial line first) and skip
corrupted lines per-session so one bad journal doesn't break the listing or
`journal --follow`. Evidence: #64, #75.

**Adding a payload key re-hashes old records.** Promote an optional key to a
typed field on an existing event type and the record hashes change → chain
break. → `EXTENSION_KEYS` is the *only* no-hash-risk way to add a payload key;
add optional data there, never as a new typed field on an existing type.
Evidence: #46.

## Honesty

**Simulated material laundered into "insights".** An interpretation derived
from simulated research silently loses its `simulated` label downstream. →
Honesty never launders: interpretations chained to simulated material inherit
the synthetic confidence class through the whole derivation. Evidence: #70.

**Machine answers presented as human testimony.** A machine-authored answer in
dojo mode gets journaled as if a human said it. → Machine answers are
`simulated`; dojo mode never journals human-only markers (e.g. `ratified`).
Evidence: #78.

## Fail-closed predicates

**A typo opens the gate / removes the budget.** An unrecognized gate policy
fails *open* (gateless session), or a typo'd budget key yields an unlimited
run. → Predicates fail **closed**: refuse an unknown gate policy at creation,
refuse a typo'd budget key instead of treating it as no-limit. Evidence: #44,
#75.

## Abstain, don't crash

**An external failure kills the whole run.** A browser that won't start, an
interview channel error, or a research fetch failure aborts the session. →
Journal an abstention and continue; an external/optional failure is never
fatal to the run. Evidence: #63, #73.

## Resume idempotence

**Founder-pick question changes on resume, MCP run can't complete.** The
mailbox key drifts between attempts so the pending question never matches the
answer. → Keep the input mailbox question id stable across resumes (key by
question text); exploration ratification is resume-idempotent for the same
reason. Evidence: #69, #78.

## Attribution

**Two records disagree about one call.** A server-side fallback serves a
different model than requested and attribution records both. → Attribute to the
model that *actually served* the call, so one contribution has one truth.
Evidence: #45 (see also `report/context.py call_cost_usd`, which prices the
served model).

## Every fix ships with its test

**A fix silently vanishes.** A batch/rebase script aborted mid-way and dropped
a behavior fix; only the commit message remembered it. The docs audit caught
the drift. → Every behavior-visible fix gets a test **in the same commit** —
the test is how we detect a dropped fix. Evidence: #66 (docs audit that
surfaced it), and the standing rule in `.claude/agents/implementer.md`.

## Models come from live docs

**A model id from memory isn't in the allowlist.** A README quickstart named a
model (`gpt-5.6-luna`) that `resolve_routing` rejects. → Take model ids, lanes,
and API shapes from live docs / `models/router.py`, never from memory. Evidence:
#44-era README fix (CHANGELOG 1.3.0).

## Release discipline (human-only, never the implementer)

**Tag disagrees with the version.** Pushing a tag whose value doesn't match
`__version__` / `server.json` ships an inconsistent release. → A version-gated
tag must equal `__version__` must equal `server.json` before the tag is pushed.
Evidence: #74.

**Assets uploaded before the release exists.** Attaching release assets before
the GitHub release object exists fails the publish. → Create the GitHub release
*first*, then upload assets. Evidence: #61.

**Release cadence is strategic, not per-PR.** Merge to main continuously; tag
and publish only at a theme/milestone/security boundary — main may sit ahead of
the latest PyPI release. (CHANGELOG header states this explicitly.)

**Git identity in this repo is personal.** Commit as the personal `maglionejm`
identity here; never the BCG account/email.
