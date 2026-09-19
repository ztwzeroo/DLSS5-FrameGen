import json
from pathlib import Path

from dlss_combo.doctor import _parse_route_active, doctor


def test_parse_active_true():
    line = json.dumps({"event": "install", "route": {"active": True, "name": "sm86"}})
    assert _parse_route_active(line + "\n") is True


def test_parse_active_false():
    line = json.dumps({"event": "install", "route": {"active": False}})
    assert _parse_route_active(line + "\n") is False


def test_parse_no_route_yields_none():
    assert _parse_route_active('{"event":"boot"}\n') is None


def test_doctor_reports_missing_route(tmp_path: Path):
    rep = doctor(tmp_path)
    assert rep.route_active is None
    assert any("dlssg_sm86" in l and "logs" in l for l in rep.lines)


def test_doctor_reads_backend_log(tmp_path: Path):
    logdir = tmp_path / "dlssg_sm86" / "logs"
    logdir.mkdir(parents=True)
    (logdir / "backend_123.jsonl").write_text(
        '{"event":"install","route":{"active":true}}\n'
    )
    rep = doctor(tmp_path)
    assert rep.route_active is True
    assert any("route" in l.lower() for l in rep.lines)


def test_doctor_flags_foreign_version_dll_conflict(tmp_path: Path):
    (tmp_path / "version.dll").write_bytes(b"x")
    rep = doctor(tmp_path)
    assert any("version.dll" in l for l in rep.lines)


def test_doctor_healthy_install(tmp_path: Path, game: Path, kit: Path):
    from dlss_combo.install import install

    install(game, kit, arch="sm86")
    logdir = game / "dlssg_sm86" / "logs"
    logdir.mkdir(parents=True)
    (logdir / "backend_9.jsonl").write_text('{"event":"install","route":{"active":true}}\n')
    rep = doctor(game)
    assert rep.route_active is True
    assert not any("missing" in l or "未检测到" in l for l in rep.lines)


def test_doctor_missing_dlss5_layer_hint(tmp_path: Path):
    rep = doctor(tmp_path)
    assert any("DLSS5-Swapper" in l or "DLSS 5" in l for l in rep.lines)
