from pathlib import Path

from bokken.journal.schema import Brief
from bokken.panel.corpus import REPO_FILE_SIZE_CAP, Corpus, ingest_repo


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
    (repo / "src" / "huge.py").write_text("x = 1\n" * (REPO_FILE_SIZE_CAP // 5))
    return repo


def test_repo_ingestion_allowlist_exclusions_and_names(tmp_path: Path) -> None:
    sources = ingest_repo(make_repo(tmp_path))
    names = {s.name for s in sources}
    assert names == {"src/main.py", "README.md"}
    assert all(s.kind == "code" for s in sources)


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
    from bokken.panel import GroundedAnswer, Interviewer, cast_panel
    from bokken.panel.corpus import Citation
    from tests.journal.conftest import SYSTEM, created_payload

    metrics = tmp_path / "kpis.csv"
    metrics.write_text("month,active_users,churn\n2026-07,1200,0.08\n")
    corpus = Corpus.ingest_inputs({"metrics": [str(metrics)]})
    source_id = corpus.ids_of_kind("metrics")[0]

    class OneShot:
        def answer(self, persona, question, context):
            return GroundedAnswer(
                text="churn was 8% in July",
                citations=[Citation(source_id=source_id, start_line=2, end_line=2)],
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
