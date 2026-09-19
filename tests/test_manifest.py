from pathlib import Path

import pytest

from dlss_combo.manifest import MANIFEST_DIR, Manifest


def _fresh() -> Manifest:
    return Manifest(
        created="2026-09-20T00:00:00",
        dlss_combo_version="0.1.0",
        dlssg={},
        files=[],
        backups=[],
    )


def test_roundtrip_and_file_hash(tmp_path: Path):
    dll = tmp_path / "version.dll"
    dll.write_bytes(b"abc")
    m = _fresh()
    sha = m.sha256_of(dll)
    m.record_file("version.dll", sha, origin="kit")
    m.record_backup("version.dll", ".dlss-combo/backups/version.dll.bak")
    m.save(tmp_path)

    m2 = Manifest.load(tmp_path)
    assert m2.files[0] == {"path": "version.dll", "sha256": sha, "origin": "kit"}
    assert m2.backups[0]["original"] == "version.dll"
    assert m2.created == "2026-09-20T00:00:00"
    assert Manifest.our_file_names(m2) == {"version.dll"}
    assert (tmp_path / MANIFEST_DIR / "manifest.json").is_file()


def test_load_missing_raises(tmp_path: Path):
    with pytest.raises(FileNotFoundError):
        Manifest.load(tmp_path)


def test_verify_detects_tampered_file(tmp_path: Path):
    dll = tmp_path / "version.dll"
    dll.write_bytes(b"abc")
    m = _fresh()
    m.record_file("version.dll", m.sha256_of(dll), origin="kit")
    m.save(tmp_path)
    dll.write_bytes(b"tampered")
    problems = Manifest.load(tmp_path).verify(tmp_path)
    assert any("version.dll" in p for p in problems)
