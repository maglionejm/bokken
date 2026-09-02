# The MCP surface

`bokken serve` exposes the entire harness over the Model Context Protocol
(stdio transport): **12 tools and 4 resources** over exactly the same core the
CLI uses, returning exactly the same JSON shapes (`src/bokken/contract.py` is
the single contract for both surfaces). Anything a human can do at the
terminal, an agent can do over MCP — create sessions, drive the loop, resolve
gates, answer Founder-mode questions, audit the ledger, and collect the
Dossier and the OpenSpec handoff.

Two properties make the surface safe to hand to agents:

- **Bounded calls.** `run_session` always returns at the next *halt*
  (`gate_pending | input_pending | stopped | completed`) — no tool call is
  open-ended. Driving a run is a plain loop: run → resolve → run.
- **Attribution.** Every state-changing call is journaled with
  `actor.kind: "agent"` and the client's *handshake* identity (name@version
  from the MCP `initialize` exchange). Identity is stamped server-side and
  cannot be supplied — or forged — via tool arguments. That includes answers:
  text submitted through `submit_input` is journaled as the client's own
  contribution in the `simulated` confidence class, never as human testimony.
  The ledger always shows whether a human or an agent approved a gate or
  answered a question.

## Setup

The server needs a provider API key in its environment for real runs:
`ANTHROPIC_API_KEY` for Anthropic sessions or `OPENAI_API_KEY` for OpenAI
sessions, and a workspace. Sessions live in `./.bokken/` relative to the server's
working directory, or wherever `BOKKEN_HOME` points — start the server where
you want the sessions to live.

**Claude Code**

```sh
claude mcp add bokken -- uv run --directory /path/to/bokken bokken serve
# or, with bokken installed as a package:
claude mcp add bokken -- bokken serve
```

**Claude Desktop** (`claude_desktop_config.json`)

```json
{
  "mcpServers": {
    "bokken": {
      "command": "uv",
      "args": ["run", "--directory", "/path/to/bokken", "bokken", "serve"],
      "env": {
        "ANTHROPIC_API_KEY": "sk-ant-...",
        "BOKKEN_HOME": "/path/to/workspace"
      }
    }
  }
}
```

**Any MCP client**: launch `bokken serve` as a stdio subprocess and speak MCP;
the server declares its tools and resource templates at initialization.

> Real Dojo stages make frontier-model calls — a single `run_session` can take
> minutes. Configure generous tool timeouts; the call always terminates at a
> halt.

## The driving loop

```
create_session_tool ──► run_session ──► halt?
                            ▲             ├─ gate_pending    ─► resolve_gate ──┐
                            │             ├─ input_pending   ─► submit_input ──┤
                            │             ├─ stopped         ─► (raise budget/stop) ─┐
                            └─────────────┴─ completed  ◄────────────────────────────┘
                                              │
                                              ▼  (automatic finalization)
                              Dossier  +  OpenSpec handoff package
```

A `completed` run is **finalized automatically** — Dossier first, then the
handoff — and the result reports it:
`"finalization": "dossier generated; handoff specs generated"`. Finalization is
idempotent, and the handoff is skipped (with the reason in the string) when the
test recommendation is `kill`.

## Tool reference

All tools take `name` — the session name — unless noted. Results are the
contract shapes shown; errors are MCP **tool errors** whose message states the
refusal (see Error semantics).

### Lifecycle

**`create_session_tool`** — create a session and journal its brief.

| Argument | Type | Default | Notes |
| --- | --- | --- | --- |
| `name` | string | — | becomes the session slug; duplicates are refused |
| `brief` | object | — | `problem_space`, `target_segments[]`, `success_criteria[]`, `risk_tolerance`, optional `constraints[]` and `inputs{repo, metrics[], discussions[], documents[]}` (paths as seen by the *server*) |
| `mode` | `"founder" \| "dojo"` | `"dojo"` | who supplies participation |
| `gate_policy` | `"none" \| "stage_boundaries" \|` string[] | mode default | dojo defaults to `stage_boundaries`, founder to `none` |
| `total_token_budget` | int | none | run-wide token budget |
| `panel_size`, `seed` | int | 6, 7 | synthetic panel casting (deterministic per brief+seed) |

Returns a **StatusResult**: `{kind:"status", name, mode, stage, state,
pending_gate?, stopped_reason?, evidence_by_class, research_debt,
options_alive, assumptions_scored, tokens_spent, last_seq, last_ts}`.

**`run_session`** — advance to the next halt. Returns a **RunOutcome**:
`{kind:"run", halt, stage, detail, pending_question?, pending_question_id?,
finalization?}`.

**`step_session`** — advance at most one stage; same shape as `run_session`.

**`stop_session`** (`reason?`) — journaled human-initiated stop; the session
stays resumable. Returns a StatusResult.

### Interaction

**`resolve_gate`** (`resolution: "approve" | "reject"`, `reason?`) — resolve
the pending gate; rejection requires a reason and keeps the session in its
stage for rework. Returns `{kind:"gate", resolution, stage}`. Errors when no
gate is pending.

**`submit_input`** (`question_id`, `answer`) — answer the pending Founder-mode
question, then call `run_session` again to consume it. The answer is attributed
to your handshake identity, so it is journaled as agent-supplied `simulated`
evidence, not as the founder's own words. Errors on a stale or unknown
`question_id` (see Founder mode below). Returns
`{stored: true, question_id, attributed_to}`.

**`request_loopback`** (`to_stage`, `reason`) — journaled human/agent-initiated
return to an earlier stage. Legal edges only: `test→define`,
`test→empathize`, `define→empathize`; anything else is a tool error naming the
legal targets. Returns `{kind:"loopback", to_stage, stage}`.

### Inspection

**`get_status`** — StatusResult for one session. `state` is one of
`in_progress | gate_pending | stopped | complete`; when a gate is pending,
`pending_gate` carries `gate_id`, the boundary, and a resolve hint.

**`list_sessions_tool`** — `{kind:"sessions", sessions:[{name, slug, stage,
mode, last_ts}]}` for the workspace.

**`query_journal`** (`type?`, `stage?`, `actor?`, `since_seq?`, `limit?`) —
ledger events in canonical form, identical to `bokken journal --json`. `type`
accepts an exact event type (`decision.recorded`) or a family (`option`);
`actor` is `human | agent | system`. See [events.md](events.md) for the
taxonomy.

### Outputs

**`generate_dossier`** — produce/refresh the Session Dossier. Returns
`{kind:"dossier", markdown_path, json_path, status: "complete"|"partial"}`.
Works mid-run (labeled partial).

**`generate_handoff`** — produce/refresh the OpenSpec MVP-spec package
([handoff.md](handoff.md)). Returns `{kind:"handoff", package_dir, change_id,
capabilities[]}`. Tool error when the session has no convergence decision or
the recommendation is `kill`.

## Resources

| URI | Content |
| --- | --- |
| `bokken://sessions` | the session list (JSON) |
| `bokken://sessions/{name}/status` | StatusResult (JSON) |
| `bokken://sessions/{name}/journal` | the full ledger, canonical JSONL |
| `bokken://sessions/{name}/dossier` | the latest `dossier.json` (error if none generated yet) |

Resources are read-only; filtered ledger access goes through `query_journal`.

## Founder mode over MCP

Founder-mode sessions ask a human questions. Over MCP there is no terminal, so
questions flow through an **input mailbox**:

1. `run_session` halts with `halt: "input_pending"`, carrying the
   `pending_question` text and a stable `pending_question_id`.
2. Obtain the answer (ask your own user, look it up, etc.) and call
   `submit_input` with that exact `question_id`.
3. Call `run_session` again — the engine consumes the answer and continues to
   the next question or halt.

A `submit_input` whose id doesn't match the currently pending question is
refused — answers can't be queued blindly against questions that were never
asked.

**The mailbox does not make you the founder.** An answer that arrives over MCP
is journaled with your handshake actor (`actor.kind: "agent"`) in the
`simulated` confidence class, sourced as `agent-supplied (<client>)`. It is a
machine contribution and Bokken labels it as one: everything derived from it
inherits the class, so Dossier lines read `synthetic` and the decisions resting
on it carry `requires_real_validation`. Relaying a real person's words through
`submit_input` does not upgrade them — only a human answering at the terminal
(or a real validation interview) produces `observed`/`reported` human evidence.
If your run needs human-grade evidence, get it from a human surface.

## Worked example: an agent runs the Dojo end to end

```
→ create_session_tool {name:"retention", mode:"dojo",
    brief:{problem_space:"commuter shuttle retention",
           target_segments:["commuters"], success_criteria:["churn below 5%"],
           risk_tolerance:"medium",
           inputs:{repo:"/work/myapp", metrics:["/work/kpis.csv"],
                   discussions:["/work/interview-ana.md"]}}}
← {kind:"status", stage:"intake", state:"in_progress", ...}

→ run_session {name:"retention"}
← {kind:"run", halt:"gate_pending", stage:"intake",
   detail:"gate g-4f2a91c0 guards intake -> empathize"}

→ resolve_gate {name:"retention", resolution:"approve"}
← {kind:"gate", resolution:"approve", stage:"intake"}

→ run_session {name:"retention"}          # … repeat approve/run per boundary …
← {kind:"run", halt:"completed", stage:"complete",
   finalization:"dossier generated; handoff specs generated"}

→ query_journal {name:"retention", type:"decision"}
← [ …every decision, with criteria, positions, and dissent… ]

→ generate_handoff {name:"retention"}
← {kind:"handoff", change_id:"build-mvp-retention",
   capabilities:["schedule-publication"],
   package_dir:".../sessions/retention/handoff"}
```

The handoff package is now on disk, OpenSpec-strict, ready for a coding agent
to ingest ([handoff.md](handoff.md)); `bokken://sessions/retention/dossier`
serves the evidence graph.

## Error semantics

Two categories, mirroring the CLI's exit codes:

| Category | Surface | Examples |
| --- | --- | --- |
| **Refused** (CLI exit 2) | tool error with the domain message | unknown session; duplicate name; no pending gate; illegal loop-back (names legal edges); stale `question_id`; handoff for a killed concept; session locked by another writer; invalid brief |
| **Unexpected** (CLI exit 1) | tool error with a generic message | provider/network failures, bugs |

Refusals never mutate state — a refused call journals nothing (with one
deliberate exception: forbidden config-change attempts are journaled as
suppressed actions, by design).

## Audit trail

Every MCP-driven action is inspectable after the fact:

```sh
bokken journal retention --actor agent           # everything agents did
bokken journal retention --type session --json \
  | jq 'select(.type=="session.gate_resolved") | {by: .actor.name, r: .payload.resolution}'
# → {"by": "claude-code@2.x", "r": "approve"}
```

## Troubleshooting

- **`session ... is locked by another writer`** — a CLI `run` (or another
  client) holds the session; state-changing tools wait their turn. Reads
  (`get_status`, `query_journal`, resources) never need the lock.
- **`no pending question with id ...`** — the question was already answered or
  the run moved on; call `run_session` and use the fresh
  `pending_question_id`.
- **`a killed concept has no build handoff`** — by design; generate the
  Dossier for the post-mortem instead.
- **Paths in `brief.inputs` resolve on the server**, not the client — pass
  absolute paths the `bokken serve` process can read.

## Report and cost tools

- `export_report(name)` — regenerates and returns the PPTX + HTML report paths (same shape as `bokken export --json`).
- `cost_report(name)` — per-stage/prompt/class cost rows with totals and cache hit rate (same data as `bokken costs --json`).

## CLI-only verbs

`bokken validate` (interactive interview channels) and `bokken library`
(workspace-level, cross-session) are CLI-first and intentionally not MCP
tools yet: the first needs a live human channel, the second reads outside
any single session. Reports and costs are available as `export_report` and
`cost_report`.
