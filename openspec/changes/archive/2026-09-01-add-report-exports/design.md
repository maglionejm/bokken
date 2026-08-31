# Design: add-report-exports

## Dependency: python-pptx

The deck must open natively in PowerPoint/Keynote (BCG deliverable norm), so
we generate real OOXML. `python-pptx` is the standard, pure-Python,
maintained library for this; writing raw OOXML by hand would be far heavier
than the dependency. The HTML export uses stdlib string templates only.

## Determinism and honesty

Both renderers consume the existing `DossierModel` (journal replay only) plus
files already on disk (handoff specs). No model calls. Cost figures are
computed from journaled `model.called` usage against a static list-price
table and labeled as estimates. The Dojo banner and synthetic-evidence counts
are carried onto the cover/summary of both formats — templates cannot drop
them because they are rendered from model fields, not re-derived.

## Deck style

Follows the house deck grammar (16:9, kicker line, statement title, content
blocks, footer with page numbers) with Bokken identity (ink/paper palette,
vermillion accent). Slide inventory is data-driven: sections with no data
(e.g. no research debt) are skipped.

## Appendix rule

One line per generated handoff spec: the capability name, the first sentence
of the spec's `## Purpose`, and the relative path to the full file. If the
handoff was refused, the appendix states the journaled refusal reason
instead. The report never re-summarizes with a model.
