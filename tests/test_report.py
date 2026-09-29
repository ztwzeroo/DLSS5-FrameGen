"""W2: report is read-only, offline, English, paste-ready."""
import json
from pathlib import Path

from dlss_combo import __version__
from dlss_combo.cli import main
from dlss_combo.manifest import VERSION
from dlss_combo.report import ISSUE_URL, build_report

CSV = "name, driver_version\nNVIDIA GeForce GT 710, 580.88\nNVIDIA GeForce RTX 3060, 581.09\n"


def _game(tmp_path: Path, *, with_manifest: bool = True) -> Path:
    g = tmp_path / "g"; g.mkdir()
    if with_manifest:
        (g / ".dlss-combo").mkdir()
        (g / ".dlss-combo" / "manifest.json").write_text(json.dumps({
            "version": VERSION, "created": "t", "dlss_combo_version": "0.1.3-test",
            "dlssg": {"commit": "c" * 40, "runtime": "310.9", "proxy_name": "version.dll",
                       "tier": 1, "mfg": "4x"},
            "files": [{"path": "version.dll", "sha256": "0" * 64, "origin": "kit"}],
            "backups": [],
        }), encoding="utf-8")
    logs = g / "dlssg_sm86" / "logs"; logs.mkdir(parents=True)
    (logs / "backend_a.jsonl").write_text(json.dumps({"route": {"active": True}}), encoding="utf-8")
    return g


def test_report_contains_all_sections(tmp_path):
    text = build_report(_game(tmp_path), gpu_runner=lambda c: CSV)
    for needle in ["game-test report", __version__, "version.dll", "RTX 3060", "(selected)",
                   "frame-gen route ACTIVE", "What this report does NOT contain"]:
        assert needle in text, needle


def test_report_without_manifest_says_so(tmp_path):
    text = build_report(_game(tmp_path, with_manifest=False), gpu_runner=lambda c: CSV)
    assert "not installed by dlss-combo" in text


def test_report_leaks_no_tmp_paths(tmp_path):
    text = build_report(_game(tmp_path), gpu_runner=lambda c: CSV)
    assert str(tmp_path) not in text


def test_report_is_english(tmp_path):
    import re
    text = build_report(_game(tmp_path), gpu_runner=lambda c: CSV)
    assert not re.search(r"[\u4e00-\u9fff]", text)


def test_cli_report_prints_and_exit_zero(tmp_path, capsys):
    rc = main(["report", str(_game(tmp_path))])
    assert rc == 0
    assert ISSUE_URL in capsys.readouterr().out
