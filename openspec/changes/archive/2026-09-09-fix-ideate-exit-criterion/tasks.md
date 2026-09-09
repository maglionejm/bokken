# Tasks: fix-ideate-exit-criterion

## 1. Implementation

- [x] 1.1 `CONCEPT_SELECTION_QUESTION` constant in machine.py; ideate branch
  of `can_exit` matches it; ideate.py and report/context.py consume the
  constant; fakes emit the canonical question; regression test for #65
  (criteria freeze alone does not open the exit)
