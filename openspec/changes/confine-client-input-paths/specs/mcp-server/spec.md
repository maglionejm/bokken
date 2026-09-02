# mcp-server Specification Delta

## ADDED Requirements

### Requirement: Client input path confinement

Paths arriving in a tool argument (the `brief.inputs` block of
`create_session`) are untrusted and SHALL be resolved only inside an authorized
input root: the workspace root (`BOKKEN_HOME`, else `./.bokken`) and the working
directory the server was started in. An input path whose resolved real path lies
outside every root — through traversal, a symlink whose target leaves the root,
or an absolute path — SHALL be refused, as SHALL a path that does not exist and
a named file outside the text allowlist. Refusals SHALL surface as tool errors
naming the path and the reason, and no session SHALL be created.

Accepted paths SHALL be journaled in resolved form, and the authorized roots
SHALL be journaled in the immutable session config snapshot so that ingestion
re-checks them when the run actually reads the files. An operator MAY widen the
roots explicitly with `BOKKEN_INPUT_ROOTS` (`os.pathsep`-separated), which
replaces the defaults; a run SHALL never widen its own roots. Operator-supplied
paths on the CLI surface SHALL remain unconfined.

#### Scenario: Named file outside the text allowlist is refused

- **WHEN** `create_session` declares `inputs.documents` naming a suffix-less file such as `id_rsa`
- **THEN** the client receives a tool error naming the allowlist, no session exists, and the file is never read

#### Scenario: Traversal out of the root is refused

- **WHEN** `create_session` declares an input path containing `../` that resolves outside the authorized roots
- **THEN** the client receives a tool error naming the roots and no session is created

#### Scenario: Escaping symlink is refused

- **WHEN** a declared input inside the root is a symlink whose target lies outside it
- **THEN** creation is refused, and a symlink swapped in after creation is skipped by the run rather than read

#### Scenario: Operator widens the roots deliberately

- **WHEN** the operator starts the server with `BOKKEN_INPUT_ROOTS` naming a research directory and a client declares an input inside it
- **THEN** the session is created, the resolved path is journaled in the brief, and the authorized roots appear in the config snapshot
