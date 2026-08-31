# Panel — spec delta (typed input sources)

## ADDED Requirements

### Requirement: Typed input sources

The evidence corpus SHALL support four source kinds declared in the session brief's `inputs` block: `code` (an application repository directory the agents explore), `metrics` (business and performance data files, CSV or JSON), `discussion` (interview transcripts, meeting notes, and needs statements), and `document` (other textual material). Ingestion SHALL record each source's kind, and repo ingestion SHALL include only recognized source-code and configuration files by extension, exclude `.git`, vendored, and binary content, enforce a per-file size cap, and name sources by repo-relative path. Every corpus-grounded evidence event and citation SHALL carry the source kind so that derived state and the Dossier can distinguish code-grounded, metrics-grounded, and human-grounded evidence.

#### Scenario: Repo becomes an explorable corpus

- **WHEN** a brief declares an app repository as a `code` input
- **THEN** its source files are ingested as citable sources named by repo-relative path, `.git` and binary files are excluded, and personas can cite code spans

#### Scenario: Evidence carries its source kind

- **WHEN** a persona answers grounded in a metrics file
- **THEN** the journaled evidence event's citations carry `source_kind: "metrics"` and the evidence is distinguishable from discussion-grounded evidence in session state

#### Scenario: Mixed inputs are independently addressable

- **WHEN** a session declares a repo, a metrics CSV, and two interview transcripts
- **THEN** the corpus exposes all sources with their kinds, and grounding scopes can select by kind (e.g. a feasibility persona scoped to `code` sources)
