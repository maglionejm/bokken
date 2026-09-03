from pathlib import Path

import pytest

from bokken.journal.schema import Brief
from bokken.panel.corpus import (
    CORPUS_SIZE_CAP,
    FILE_SIZE_CAP,
    INPUT_ROOTS_ENV,
    Corpus,
    InputPathRefused,
    confine_inputs,
    confine_path,
    ingest_repo,
    input_roots,
)


def make_repo(tmp_path: Path) -> Path:
    repo = tmp_path / "app"
    (repo / "src").mkdir(parents=True)
    (repo / ".git").mkdir()
    (repo / "node_modules" / "lib").mkdir(parents=True)
    (repo / "src" / "main.py").write_text("def handler():\n    return 'ok'\n")
    (repo / "README.md").write_text("# The app\nA commuter shuttle app.\n")
    (repo / ".git" / "config").write_text("[core]\n")
    (repo / "node_modules" / "lib" / "index.js").write_text("module.exports = 1\n")
    (repo / "logo.png").write_bytes(b"\x89PNG\r\n")
    (repo / "src" / "huge.py").write_text("x = 1\n" * (FILE_SIZE_CAP // 5))
    return repo


def test_repo_ingestion_allowlist_exclusions_and_names(tmp_path: Path) -> None:
    sources, skipped = ingest_repo(make_repo(tmp_path))
    names = {s.name for s in sources}
    assert names == {"src/main.py", "README.md"}
    assert all(s.kind == "code" for s in sources)
    assert skipped == []


def test_mixed_inputs_are_independently_addressable(tmp_path: Path) -> None:
    repo = make_repo(tmp_path)
    metrics = tmp_path / "kpis.csv"
    metrics.write_text("month,active_users,churn\n2026-07,1200,0.08\n")
    interview_a = tmp_path / "interview-a.md"
    interview_a.write_text("I stopped using the app because arrivals were unpredictable.\n")
    interview_b = tmp_path / "interview-b.txt"
    interview_b.write_text("Operators need route-change notice a day ahead.\n")

    brief = Brief.model_validate(
        {
            "problem_space": "commuter shuttle retention",
            "target_segments": ["commuters"],
            "success_criteria": ["churn below 5%"],
            "risk_tolerance": "medium",
            "inputs": {
                "repo": str(repo),
                "metrics": [str(metrics)],
                "discussions": [str(interview_a), str(interview_b)],
            },
        }
    )
    corpus = Corpus.ingest_inputs(brief.inputs.model_dump())
    assert len(corpus.ids_of_kind("code")) == 2
    assert len(corpus.ids_of_kind("metrics")) == 1
    assert len(corpus.ids_of_kind("discussion")) == 2
    assert set(corpus.ids_of_kind("code", "metrics")) < set(corpus.source_ids)
    context = corpus.context_for(corpus.ids_of_kind("metrics"))
    assert "kpis.csv" in context and "(metrics)" in context


def test_citation_kind_lands_in_evidence(tmp_path: Path) -> None:
    from bokken.journal import JournalStore
    from bokken.models.router import Attributed, Attribution
    from bokken.panel import GroundedAnswer, Interviewer, cast_panel
    from bokken.panel.corpus import Citation
    from tests.journal.conftest import SYSTEM, created_payload

    metrics = tmp_path / "kpis.csv"
    metrics.write_text("month,active_users,churn\n2026-07,1200,0.08\n")
    corpus = Corpus.ingest_inputs({"metrics": [str(metrics)]})
    source_id = corpus.ids_of_kind("metrics")[0]

    class OneShot:
        def answer(self, persona, question, context):
            return Attributed(
                data=GroundedAnswer(
                    text="churn was 8% in July",
                    citations=[Citation(source_id=source_id, start_line=2, end_line=2)],
                ),
                attribution=Attribution("claude-opus-4-8"),
            )

    with JournalStore.open(tmp_path / "session") as store:
        store.append(
            type="session.created", stage="intake", actor=SYSTEM, payload=created_payload()
        )
        persona = cast_panel(brief={"target_segments": ["commuters"]}, size=4, seed=1)[3]
        event = Interviewer(corpus, OneShot(), store).ask(
            persona, "what does churn look like?", stage="empathize"
        )
    assert event.payload["citations"][0]["source_kind"] == "metrics"


# --- ingestion narrowness and root confinement --------------------------------


def test_named_file_outside_the_text_allowlist_is_reported_not_read(tmp_path: Path) -> None:
    """The suffix allowlist applies to explicitly named files, not only to walks."""
    secret = tmp_path / "id_rsa"
    secret.write_text("-----BEGIN OPENSSH PRIVATE KEY-----\nhunter2\n")

    corpus = Corpus.ingest_inputs({"documents": [str(secret)]})

    assert corpus.source_ids == []
    assert "hunter2" not in corpus.context_for()
    assert [s.path for s in corpus.skipped] == [str(secret)]
    assert "allowlist" in corpus.skipped[0].reason


def test_named_directory_walk_is_bounded_by_the_corpus_cap(tmp_path: Path) -> None:
    tree = tmp_path / "notes"
    (tree / "deep").mkdir(parents=True)
    for i in range(30):
        (tree / "deep" / f"note-{i}.md").write_text("x" * (FILE_SIZE_CAP - 1))

    corpus = Corpus.ingest_inputs({"documents": [str(tree)]})

    ingested = len(corpus.source_ids)
    assert 0 < ingested < 30
    assert ingested * (FILE_SIZE_CAP - 1) <= CORPUS_SIZE_CAP
    assert any("corpus cap" in s.reason for s in corpus.skipped)


def test_single_oversized_file_is_reported_not_read(tmp_path: Path) -> None:
    fat = tmp_path / "dump.json"
    fat.write_text("[" + "0," * FILE_SIZE_CAP + "0]")

    corpus = Corpus.ingest_inputs({"documents": [str(fat)]})

    assert corpus.source_ids == []
    assert [s.reason for s in corpus.skipped] == [f"larger than the {FILE_SIZE_CAP}-byte file cap"]


def test_confinement_refuses_traversal_symlinks_and_outside_paths(tmp_path: Path) -> None:
    root = tmp_path / "workspace"
    root.mkdir()
    outside = tmp_path / "outside"
    outside.mkdir()
    (outside / "secrets.md").write_text("the launch codes\n")
    (root / "escape.md").symlink_to(outside / "secrets.md")
    inside = root / "notes.md"
    inside.write_text("a real note\n")
    roots = (root,)

    assert confine_path("notes.md", roots) == inside.resolve()
    assert confine_path(str(inside), roots) == inside.resolve()

    for raw in ("../outside/secrets.md", str(outside / "secrets.md"), "escape.md", "/etc/hosts"):
        with pytest.raises(InputPathRefused):
            confine_path(raw, roots)

    with pytest.raises(InputPathRefused):
        confine_path("absent.md", roots)


def test_confined_inputs_block_is_rewritten_to_resolved_paths(tmp_path: Path) -> None:
    root = tmp_path / "workspace"
    (root / "data").mkdir(parents=True)
    (root / "data" / "kpis.csv").write_text("month,churn\n2026-07,0.08\n")
    repo = make_repo(root)

    confined = confine_inputs({"metrics": ["data/kpis.csv"], "repo": "app"}, (root,))

    assert confined["metrics"] == [str((root / "data" / "kpis.csv").resolve())]
    assert confined["repo"] == str(repo.resolve())

    with pytest.raises(InputPathRefused):
        confine_inputs({"documents": [str(tmp_path / "elsewhere.md")]}, (root,))


def test_confined_run_skips_inputs_that_escape_the_root(tmp_path: Path) -> None:
    """Defense in depth: the run re-checks the journaled roots when it reads."""
    root = tmp_path / "workspace"
    root.mkdir()
    outside = tmp_path / "outside"
    outside.mkdir()
    (outside / "secrets.md").write_text("the launch codes\n")
    swapped = root / "notes.md"
    swapped.symlink_to(outside / "secrets.md")  # symlinked after creation-time checks

    corpus = Corpus.ingest_inputs({"documents": [str(swapped)]}, roots=[root])

    assert corpus.source_ids == []
    assert "launch codes" not in corpus.context_for()
    assert [s.reason for s in corpus.skipped] == ["outside the authorized input root"]


def test_default_input_roots_cover_the_working_directory(tmp_path: Path) -> None:
    assert tmp_path.resolve() in input_roots(base=tmp_path)


def test_input_roots_override_replaces_the_default(tmp_path: Path, monkeypatch) -> None:
    widened = tmp_path / "shared"
    widened.mkdir()
    monkeypatch.setenv(INPUT_ROOTS_ENV, str(widened))
    assert input_roots(base=tmp_path) == (widened.resolve(),)


def test_rejected_input_lands_in_the_journal(tmp_path: Path) -> None:
    from bokken.journal import JournalStore
    from bokken.stages.base import journal_rejected_inputs
    from tests.journal.conftest import SYSTEM, created_payload

    secret = tmp_path / "id_rsa"
    secret.write_text("-----BEGIN OPENSSH PRIVATE KEY-----\n")
    corpus = Corpus.ingest_inputs({"documents": [str(secret)]})

    with JournalStore.open(tmp_path / "session") as store:
        store.append(
            type="session.created", stage="intake", actor=SYSTEM, payload=created_payload()
        )
        journal_rejected_inputs(store, corpus, stage="empathize")
        rejected = [e for e in store.events() if e.type == "evidence.input_rejected"]

    assert [e.payload["path"] for e in rejected] == [str(secret)]
    assert "allowlist" in rejected[0].payload["reason"]
