# cli

## ADDED Requirements

### Requirement: Pack verb

`bokken pack NAME` SHALL produce a single zip archive containing a
`manifest.json` (bokken version, session facts, verdict, list-price cost,
packed-at timestamp, and a per-file index with sizes and sha256 digests)
plus the session's deliverables: self-contained HTML report, deck, dossier,
and handoff tree. By default the journal, evidence graph, and artifacts are
included; `--deliverables-only` SHALL omit them and the manifest SHALL state
the omission and its verifiability consequence. Packing SHALL never mutate
the session, and an unfinalized session SHALL be refused with exit 2 and a
pointer to `bokken export`.

#### Scenario: The run as one portable object

- **WHEN** `bokken pack retention` runs on a finalized session
- **THEN** `retention.bokken.zip` exists with a manifest whose file index digests match the packed files, and the report inside opens offline

#### Scenario: External sharing is honest about omissions

- **WHEN** `bokken pack retention --deliverables-only` runs
- **THEN** the bundle omits journal, dossier.json, and artifacts, and the manifest states that claims are not independently verifiable from the bundle alone

#### Scenario: Unfinalized sessions are refused

- **WHEN** `bokken pack` targets a session with no report
- **THEN** it exits 2 telling the operator to run `bokken export` first
