from pathlib import Path

import pytest

from bokken.journal import JournalStore, replay
from bokken.panel import (
    Abstention,
    CastingError,
    Citation,
    ContaminationError,
    ConvergenceBlockedError,
    Corpus,
    CriteriaFrozenError,
    GroundedAnswer,
    Interviewer,
    Persona,
    ProfileOpinion,
    cast_panel,
    check_firewall,
    freeze_criteria,
    frozen_criteria,
    grounding_health,
    journal_manifest,
    require_skeptic_challenge,
    requires_real_validation,
    strip_preferences,
    validate_panel_config,
)
from tests.journal.conftest import AGENT, BRIEF, SYSTEM, created_payload

TWO_SEGMENT_BRIEF = {**BRIEF, "target_segments": ["commuters", "operators"]}


@pytest.fixture
def store(tmp_path: Path):
    with JournalStore.open(tmp_path / "panel-session") as s:
        s.append(
            type="session.created",
            stage="intake",
            actor=SYSTEM,
            payload=created_payload(mode="dojo"),
        )
        yield s


@pytest.fixture
def corpus(tmp_path: Path) -> Corpus:
    doc = tmp_path / "voc.md"
    doc.write_text("commuters hate unpredictable arrival times\nbikes rust in winter\n")
    return Corpus.ingest([doc])


# --- casting ----------------------------------------------------------------


def test_casting_covers_segments_and_roles() -> None:
    panel = cast_panel(brief=TWO_SEGMENT_BRIEF, size=8, seed=42)
    assert len(panel) == 8
    roles = {p.role for p in panel}
    assert {"skeptic", "feasibility", "viability", "segment"} == roles
    segments = {p.segment for p in panel if p.role == "segment"}
    assert segments == {"commuters", "operators"}
    for p in panel:
        assert p.profile and len(p.ocean) == 5


def test_casting_is_reproducible_and_seed_sensitive() -> None:
    a = cast_panel(brief=TWO_SEGMENT_BRIEF, size=8, seed=42)
    b = cast_panel(brief=TWO_SEGMENT_BRIEF, size=8, seed=42)
    c = cast_panel(brief=TWO_SEGMENT_BRIEF, size=8, seed=43)
    assert a == b
    assert {p.persona_id for p in a} != {p.persona_id for p in c}


def test_too_small_panel_is_refused() -> None:
    with pytest.raises(CastingError, match="minimum"):
        cast_panel(brief=TWO_SEGMENT_BRIEF, size=4, seed=1)


def test_manifest_is_journaled_before_content(store: JournalStore) -> None:
    panel = cast_panel(brief=TWO_SEGMENT_BRIEF, size=6, seed=7)
    event = journal_manifest(store, personas=panel, panel_kind="ideation", seed=7, stage="ideate")
    assert event.payload["kind"] == "panel_manifest"
    assert set(event.payload["persona_ids"]) == {p.persona_id for p in panel}
    assert (store.session_dir / event.payload["path"]).exists()


# --- corpus and grounding ---------------------------------------------------


def test_corpus_span_resolution(corpus: Corpus) -> None:
    source_id = corpus.source_ids[0]
    assert corpus.validate_citation(Citation(source_id=source_id, start_line=1, end_line=1))
    assert not corpus.validate_citation(Citation(source_id=source_id, start_line=5, end_line=9))
    assert not corpus.validate_citation(Citation(source_id="nope", start_line=1, end_line=1))


class ScriptedGenerator:
    model = "claude-fable-5"

    def __init__(self, results) -> None:
        self.results = list(results)

    def answer(self, persona, question, context):
        return self.results.pop(0)


def _segment_persona() -> Persona:
    return cast_panel(brief=TWO_SEGMENT_BRIEF, size=6, seed=7)[3]


def test_grounded_answer_is_simulated_with_citations(store, corpus) -> None:
    source_id = corpus.source_ids[0]
    generator = ScriptedGenerator(
        [
            GroundedAnswer(
                text="arrival predictability is the pain",
                citations=[Citation(source_id=source_id, start_line=1, end_line=1)],
            )
        ]
    )
    event = Interviewer(corpus, generator, store).ask(
        _segment_persona(), "what frustrates you?", stage="empathize"
    )
    assert event.type == "evidence.captured"
    assert event.payload["confidence_class"] == "simulated"
    assert event.payload["grounding"] == "corpus"
    assert event.payload["citations"][0]["source_id"] == source_id
    assert event.actor.persona_id is not None


def test_ungrounded_question_becomes_research_debt(store, corpus) -> None:
    generator = ScriptedGenerator([Abstention(reason="no pricing data in corpus")])
    event = Interviewer(corpus, generator, store).ask(
        _segment_persona(), "willingness to pay?", stage="empathize"
    )
    assert event.type == "evidence.abstained"
    state = replay(store.events())
    assert len(state.research_debt) == 1
    assert state.research_debt[0].question == "willingness to pay?"


def test_invalid_citation_is_converted_to_abstention(store, corpus) -> None:
    generator = ScriptedGenerator(
        [
            GroundedAnswer(
                text="fabricated",
                citations=[Citation(source_id="bogus", start_line=1, end_line=2)],
            )
        ]
    )
    event = Interviewer(corpus, generator, store).ask(
        _segment_persona(), "how many users churn?", stage="empathize"
    )
    assert event.type == "evidence.abstained"
    assert "citation_invalid" in event.payload["gap"]


def test_grounding_health_separates_backstop_abstentions_from_real_gaps(store, corpus) -> None:
    """A paraphrasing sidekick would show up here, not as silent research debt."""
    source_id = corpus.source_ids[0]
    generator = ScriptedGenerator(
        [
            GroundedAnswer(
                text="arrival predictability is the pain",
                citations=[Citation(source_id=source_id, start_line=1, end_line=1)],
            ),
            GroundedAnswer(  # paraphrased span: the backstop cannot resolve it
                text="paraphrased",
                citations=[Citation(source_id="bogus", start_line=1, end_line=2)],
            ),
            Abstention(reason="no pricing data in corpus"),
        ]
    )
    interviewer = Interviewer(corpus, generator, store)
    persona = _segment_persona()
    for question in ("what frustrates you?", "how many churn?", "willingness to pay?"):
        interviewer.ask(persona, question, stage="empathize")
    # A stage-level research gap is not a persona turn and must not dilute it.
    store.append(
        type="evidence.abstained",
        stage="prototype",
        actor=AGENT,
        payload={"question": "Concept research on the live web", "gap": "web research not allowed"},
    )
    health = grounding_health(store.events())
    assert health["persona_turns"] == 3
    assert health["abstentions"] == 2
    assert health["citation_invalid_abstentions"] == 1
    assert health["citation_invalid_rate"] == pytest.approx(0.333, abs=0.001)


def test_profile_opinion_is_marked_profile_derived(store, corpus) -> None:
    generator = ScriptedGenerator([ProfileOpinion(text="I prefer predictable routines")])
    event = Interviewer(corpus, generator, store).ask(
        _segment_persona(), "how do you feel about change?", stage="empathize"
    )
    assert event.payload["grounding"] == "profile"
    assert event.payload["confidence_class"] == "simulated"


# --- firewall ---------------------------------------------------------------


def test_fresh_test_panel_passes_and_is_journaled(store) -> None:
    ideation = cast_panel(brief=TWO_SEGMENT_BRIEF, size=6, seed=1)
    journal_manifest(store, personas=ideation, panel_kind="ideation", seed=1, stage="ideate")
    test_panel = cast_panel(brief=TWO_SEGMENT_BRIEF, size=6, seed=2)
    event = check_firewall(store, test_panel)
    assert event.payload["resolution"] == "disjoint"


def test_contaminated_panel_is_refused_before_evaluation(store) -> None:
    ideation = cast_panel(brief=TWO_SEGMENT_BRIEF, size=6, seed=1)
    journal_manifest(store, personas=ideation, panel_kind="ideation", seed=1, stage="ideate")
    with pytest.raises(ContaminationError):
        check_firewall(store, ideation[:4])
    refusals = [
        e
        for e in store.events()
        if e.type == "decision.recorded" and "refused" in e.payload["resolution"]
    ]
    assert len(refusals) == 1


# --- anti-sycophancy and labeling --------------------------------------------


def test_preference_markers_never_reach_personas() -> None:
    material = {
        "problem_space": "mobility",
        "sponsor_hypothesis": "we already know subscriptions win",
        "options": [{"name": "a", "preferred": True}, {"name": "b"}],
    }
    clean = strip_preferences(material)
    assert "sponsor_hypothesis" not in clean
    assert all("preferred" not in o for o in clean["options"])
    assert clean["problem_space"] == "mobility"


def test_criteria_freeze_before_options_and_immutability(store) -> None:
    freeze_criteria(store, criteria=["desirability", "feasibility", "viability"])
    with pytest.raises(CriteriaFrozenError, match="already frozen"):
        freeze_criteria(store, criteria=["speed only"])
    state = replay(store.events())
    assert frozen_criteria(state) == ["desirability", "feasibility", "viability"]


def test_criteria_cannot_freeze_after_options_exist(store) -> None:
    store.append(type="option.created", stage="ideate", actor=AGENT, payload={"summary": "x"})
    with pytest.raises(CriteriaFrozenError, match="before any option"):
        freeze_criteria(store, criteria=["dfv"])


def test_skeptic_quota_blocks_convergence(store, corpus) -> None:
    panel = cast_panel(brief=TWO_SEGMENT_BRIEF, size=6, seed=7)
    skeptic = next(p for p in panel if p.role == "skeptic")
    state = replay(store.events())
    with pytest.raises(ConvergenceBlockedError):
        require_skeptic_challenge(state, {skeptic.persona_id})

    generator = ScriptedGenerator([ProfileOpinion(text="the demand claim is untested")])
    Interviewer(corpus, generator, store).ask(skeptic, "challenge the consensus", stage="ideate")
    state = replay(store.events())
    require_skeptic_challenge(state, {skeptic.persona_id})  # no raise


def test_validation_flag_propagates_through_insights(store, corpus) -> None:
    source_id = corpus.source_ids[0]
    generator = ScriptedGenerator(
        [
            GroundedAnswer(
                text="predictability pain",
                citations=[Citation(source_id=source_id, start_line=1, end_line=1)],
            )
        ]
    )
    evidence = Interviewer(corpus, generator, store).ask(
        _segment_persona(), "pain?", stage="empathize"
    )
    insight = store.append(
        type="interpretation.derived",
        stage="define",
        actor=AGENT,
        payload={"kind": "insight", "statement": "predictability wins"},
        refs=[evidence.id],
    )
    state = replay(store.events())
    assert requires_real_validation(state, [insight.id]) is True


def test_labeling_cannot_be_configured_away() -> None:
    validate_panel_config({"panel": {"size": 8}})  # fine
    for key in ("label_synthetic", "disable_synthetic_labels", "suppress_validation_flags"):
        with pytest.raises(Exception, match="cannot be disabled"):
            validate_panel_config({"panel": {key: False}})
