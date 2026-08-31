# Proposal: fix-test-artifact-selection

## Why

Live-run defect (vatios session): the Test engine passed `artifacts[0]` to evaluators, which is the panel-manifest JSON, not the prototype - personas reviewed a roster instead of the storyboard/landing copy. The stages spec already requires evaluating prototype artifacts; this restores compliance (no spec-level change).

## What Changes

- Test engine selects the first artifact of a prototype kind (concept_one_pager, landing_copy, storyboard, demo_script); manifests and other bookkeeping artifacts are never shown to evaluators.
- Offline e2e now asserts evaluators never see manifest content.

## Capabilities

### New Capabilities

(none)

### Modified Capabilities

(none - defect fix restoring existing spec behavior; skip_specs)

## Impact

`src/bokken/stages/testing.py`; fake-provider assertion.
