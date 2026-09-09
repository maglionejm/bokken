"""bokken pack: one portable archive per finalized run (issue #48)."""

from __future__ import annotations

import json
import zipfile

import pytest

from bokken.demo import run_demo


@pytest.fixture(scope="module")
def finalized(tmp_path_factory):
    home = tmp_path_factory.mktemp("pack-home")
    mp = pytest.MonkeyPatch()
    mp.setenv("BOKKEN_HOME", str(home))
    mp.delenv("ANTHROPIC_API_KEY", raising=False)
    try:
        yield run_demo("packable")
    finally:
        mp.undo()


def test_full_pack_carries_journal_and_manifest(finalized):
    from bokken.bundle import pack_session

    bundle = pack_session(finalized["session_dir"])
    with zipfile.ZipFile(bundle) as zf:
        names = set(zf.namelist())
        manifest = json.loads(zf.read("manifest.json"))
    assert "journal.jsonl" in names
    assert "report/report.html" in names and "report/report.pptx" in names
    assert "dossier/dossier.json" in names
    assert any(n.startswith("handoff/") for n in names)
    assert manifest["contents"] == "full"
    assert manifest["verdict"] == "iterate"
    assert manifest["demo"] is True
    assert all({"path", "bytes", "sha256"} <= set(f) for f in manifest["files"])


def test_deliverables_only_omits_and_says_so(finalized):
    from bokken.bundle import pack_session

    bundle = pack_session(finalized["session_dir"], deliverables_only=True)
    with zipfile.ZipFile(bundle) as zf:
        names = set(zf.namelist())
        manifest = json.loads(zf.read("manifest.json"))
    assert "journal.jsonl" not in names
    assert "dossier/dossier.json" not in names
    assert not any(n.startswith("artifacts/") for n in names)
    assert "report/report.html" in names
    assert manifest["contents"] == "deliverables-only"
    assert "omitted" in manifest


def test_pack_refuses_unfinalized_session(tmp_path):
    from bokken.bundle import PackError, pack_session

    bare = tmp_path / "bare"
    bare.mkdir()
    with pytest.raises(PackError, match="bokken export"):
        pack_session(bare)


def test_manifest_hashes_match_archived_bytes_when_files_change_mid_pack(
    finalized, tmp_path, monkeypatch
):
    """A live session can rewrite a deliverable while pack runs; the manifest
    and the archive must still agree because each file is read exactly once."""
    import hashlib
    import shutil

    import bokken.bundle as bundle

    session_dir = tmp_path / "live"
    shutil.copytree(finalized["session_dir"], session_dir)
    report = session_dir / "report" / "report.html"
    real_cost = bundle._cost

    def cost_and_mutate(sd):
        # Runs between manifest assembly and archiving in a torn implementation.
        report.write_text(report.read_text() + "<!-- appended by a live run -->")
        return real_cost(sd)

    monkeypatch.setattr(bundle, "_cost", cost_and_mutate)
    out = bundle.pack_session(session_dir)
    with zipfile.ZipFile(out) as zf:
        manifest = json.loads(zf.read("manifest.json"))
        for entry in manifest["files"]:
            data = zf.read(entry["path"])
            assert hashlib.sha256(data).hexdigest() == entry["sha256"]
            assert len(data) == entry["bytes"]
