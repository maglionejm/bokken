# panel Specification Delta

## MODIFIED Requirements

### Requirement: Typed input sources

The evidence corpus SHALL support four source kinds declared in the session brief's `inputs` block: `code` (an application repository directory the agents explore), `metrics` (business and performance data files, CSV or JSON), `discussion` (interview transcripts, meeting notes, and needs statements), and `document` (other textual material). Ingestion SHALL record each source's kind, and repo ingestion SHALL include only recognized source-code and configuration files by extension, exclude `.git`, vendored, and binary content, enforce a per-file size cap, and name sources by repo-relative path. Every corpus-grounded evidence event and citation SHALL carry the source kind so that derived state and the Dossier can distinguish code-grounded, metrics-grounded, and human-grounded evidence.

Text ingestion SHALL apply its suffix allowlist to explicitly named files as well as to directory walks, SHALL enforce a per-file size cap and a total cap per ingested set so that no single file or directory walk can balloon the corpus, and SHALL NOT read anything outside those bounds. When a session's config snapshot declares authorized input roots, ingestion SHALL re-check every declared input against them and skip whatever resolves outside, so that confinement granted at creation cannot be widened later by a swapped symlink. A declared input that is refused, missing, or capped SHALL be journaled as `evidence.input_rejected` naming the path and the reason — never dropped silently, because the corpus decides what personas can be grounded in.

#### Scenario: Repo becomes an explorable corpus

- **WHEN** a brief declares an app repository as a `code` input
- **THEN** its source files are ingested as citable sources named by repo-relative path, `.git` and binary files are excluded, and personas can cite code spans

#### Scenario: Evidence carries its source kind

- **WHEN** a persona answers grounded in a metrics file
- **THEN** the journaled evidence event's citations carry `source_kind: "metrics"` and the evidence is distinguishable from discussion-grounded evidence in session state

#### Scenario: Mixed inputs are independently addressable

- **WHEN** a session declares a repo, a metrics CSV, and two interview transcripts
- **THEN** the corpus exposes all sources with their kinds, and grounding scopes can select by kind (e.g. a feasibility persona scoped to `code` sources)

#### Scenario: Named file outside the allowlist is never read

- **WHEN** a brief declares a suffix-less file (for example a private key) as a `document` input
- **THEN** the file's content enters neither the corpus nor any rendered prompt, and the skip is journaled as `evidence.input_rejected`

#### Scenario: A directory walk cannot balloon the corpus

- **WHEN** a declared `document` directory contains more allowlisted text than the corpus cap
- **THEN** ingestion stops at the cap, a file above the per-file cap is left out, and each omission is journaled with its reason

#### Scenario: Confined run skips an input that escapes its roots

- **WHEN** a session whose config declares authorized input roots ingests a declared input that now resolves outside them
- **THEN** the input is skipped with reason, the run continues on the remaining grounding, and nothing outside the roots is read
