"""W5(a): session verdict = LAST route event of the NEWEST log; degraded reads are problems;
image-layer files are evidence, never activation."""
import json
from pathlib import Path

from dlss_combo.doctor import doctor


def _mklog(game: Path, name: str, events: list[bool]) -> None:
    d = game / "dlssg_sm86" / "logs"
    d.mkdir(parents=True, exist_ok=True)
    lines = [{"route": {"active": a}} for a in events]
    (d / name).write_text("\n".join(json.dumps(x) for x in lines), encoding="utf-8")


def test_same_log_earlier_success_later_failure_wins(tmp_path):
    game = tmp_path / "g"; game.mkdir()
    _mklog(game, "backend_a.jsonl", [True, True, False])
    rep = doctor(game)
    assert rep.route_active is False
    assert rep.has_problems


def test_newest_log_failure_beats_older_success(tmp_path):
    import os, time
    game = tmp_path / "g"; game.mkdir()
    _mklog(game, "backend_old.jsonl", [True])
    _mklog(game, "backend_new.jsonl", [False])
    old = game / "dlssg_sm86" / "logs" / "backend_old.jsonl"
    new = game / "dlssg_sm86" / "logs" / "backend_new.jsonl"
    t = time.time(); os.utime(old, (t - 100, t - 100)); os.utime(new, (t, t))
    rep = doctor(game)
    assert rep.route_active is False
    assert any("historical" in ln.lower() or "更早" in ln for ln in rep.lines)


def test_unreadable_log_is_a_problem_not_a_crash(tmp_path, monkeypatch):
    game = tmp_path / "g"; game.mkdir()
    _mklog(game, "backend_x.jsonl", [True])
    from dlss_combo import doctor as doc
    def boom(self, *a, **k):
        raise OSError("permission denied")
    monkeypatch.setattr(doc.Path, "read_text", boom)
    rep = doctor(game)
    assert rep.has_problems
    assert any("unreadable" in p for p in rep.problems)


def test_reshade_files_are_evidence_not_activation(tmp_path):
    game = tmp_path / "g"; game.mkdir()
    (game / "ReShade.ini").write_text("[GENERAL]\n", encoding="utf-8")
    _mklog(game, "backend_y.jsonl", [True])
    rep = doctor(game)
    assert rep.route_active is True          # route verdict unaffected by image layer
    assert "ReShade" in getattr(rep, "image_layer_files", [])
    assert not any("active" in p for p in rep.problems if "route" in p)
