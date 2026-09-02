# models Specification Delta

## MODIFIED Requirements

### Requirement: Parallel prompt caches

Prompts MAY declare a cache split: the provider SHALL send everything before
the split as a cache-controlled block so each lane keeps its own persistent
cached prefix (the sidekick's corpus, the persona panel's corpus, the lens
prompts' shared option set, the test panel's artifact). Per-call journaled usage
SHALL carry cache-read tokens so `bokken costs` can report hit rates. Switching
lanes SHALL never invalidate the other lane's cache (they are per-model by
construction).

A template that declares a cache split SHALL place every parameter that is
shared across the calls in its loop before the split, and every parameter that
varies per call after it, so that the cacheable prefix is byte-identical for
each call in the loop. A cache split SHALL NOT be declared on a template whose
prefix varies per call or is smaller than the routed models' minimum cacheable
prefix, since a cache write costs more than fresh input and such a prefix could
never be read back. Delegated retrieval that feeds a cached prefix SHALL be
reused across the calls that share that prefix rather than re-issued per call.

Rendered prompt text SHALL be identical whether or not a template declares a
split - the marker is provider framing only, never model-visible content - so
the journaled prompt hash keeps matching the wire payload for every adapter.

#### Scenario: The corpus is paid for once

- **WHEN** twelve interview turns run against the same corpus within the cache TTL
- **THEN** the corpus tokens are written once and read from cache thereafter, and the cost report shows a non-zero cache hit rate

#### Scenario: Shared material leads the persona turn

- **WHEN** several personas answer one question over one corpus
- **THEN** each rendered persona turn carries a byte-identical cacheable prefix holding the corpus, with the persona and the question after the split

#### Scenario: One artifact serves the whole assumption register

- **WHEN** a test panel evaluates one prototype artifact once per assumption
- **THEN** the artifact sits in the cacheable prefix and the persona and assumption under test sit after the split

#### Scenario: One option set serves every convergence lens

- **WHEN** the feasibility, viability, and desirability lenses vote on the same frozen options
- **THEN** the problem, criteria, and option set are written to cache once and read back by the remaining lenses, with each lens's own instructions after the split

#### Scenario: Retrieval is not re-issued per persona

- **WHEN** an interview turn faces a corpus above the delegation threshold and every persona on the panel is asked that question
- **THEN** the sidekick retrieves the spans once and every persona turn receives that identical retrieval

#### Scenario: A prefix too small to cache declares no split

- **WHEN** a per-call loop's shared material is smaller than the routed models' minimum cacheable prefix
- **THEN** the template still orders that material before the varying material but declares no cache split

## ADDED Requirements

### Requirement: Delegation must beat cached retrieval

Fusion delegation to the sidekick SHALL be triggered only where it beats sending
the corpus itself, accounting for the persona turn's cached corpus prefix: an
undelegated corpus is paid once at the cache-write premium and read back at a
fraction of fresh input, while delegation additionally pays the sidekick's
retrieval output at frontier output prices for every distinct question. The
delegation threshold SHALL be documented in the code with that rationale, and
crossing it SHALL remain journaled as a sidekick call.

#### Scenario: A moderate corpus is sent rather than delegated

- **WHEN** an interview turn faces a corpus below the delegation threshold
- **THEN** no sidekick call is made and the corpus is sent as the turn's cacheable prefix

#### Scenario: A very large corpus is still delegated

- **WHEN** an interview turn faces a corpus above the delegation threshold
- **THEN** a sidekick call retrieves source-marked spans, the frontier turn receives only those slices, and both calls are journaled
