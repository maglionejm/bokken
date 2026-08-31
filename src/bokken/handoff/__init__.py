"""The handoff: OpenSpec MVP specifications from a completed run.

The Dossier explains what was learned; the handoff turns the validated concept
into build-ready OpenSpec specifications another harness component can ingest.
"""

from bokken.handoff.finalize import FinalizeResult, finalize_session
from bokken.handoff.generate import (
    HandoffGenerationError,
    HandoffRefusedError,
    generate_handoff,
    handoff_exists,
)
from bokken.handoff.render import HandoffFormatError, validate_package
from bokken.handoff.schema import SpecPackage

__all__ = [
    "FinalizeResult",
    "HandoffFormatError",
    "HandoffGenerationError",
    "HandoffRefusedError",
    "SpecPackage",
    "finalize_session",
    "generate_handoff",
    "handoff_exists",
    "validate_package",
]
