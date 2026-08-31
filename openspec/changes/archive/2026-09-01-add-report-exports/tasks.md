# Tasks: add-report-exports

## 1. Report module

- [x] 1.1 `report/context.py`: derive report context from DossierModel —
  cost estimate from journaled usage, spec appendix entries from handoff
  files or refusal reason; verify with unit tests on a completed fixture
- [x] 1.2 `report/deck.py`: python-pptx renderer (kicker/title/footer
  grammar, data-driven slide inventory); verify the deck opens via
  python-pptx round-trip and carries the banner
- [x] 1.3 `report/page.py`: self-contained HTML renderer with the same
  sections; verify required content is present in the output string

## 2. Wiring

- [x] 2.1 Finalization generates the report after dossier + handoff,
  idempotently; verify via offline e2e (iterate and kill paths)
- [x] 2.2 CLI `export` verb with `--json`; verify via CLI test

## 3. Definition of done

- [x] 3.1 `make check` green; live export produced for the
  `vatios-engagement` session
