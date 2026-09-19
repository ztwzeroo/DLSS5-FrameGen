"""缺口补齐：驱动版本检查 + --launch-swapper。"""
import json
from pathlib import Path

import pytest

from dlss_combo.cli import main
from dlss_combo.fetch import launch_swapper
from dlss_combo.gpu import MIN_DRIVER_MAJOR, driver_meets_minimum
from tests.conftest import make_kit


# ---------- 缺口 1：驱动 ≥ R580 检查 ----------

def test_min_driver_constant():
    assert MIN_DRIVER_MAJOR == 580


def test_driver_meets_minimum():
    assert driver_meets_minimum("591.86") is True
    assert driver_meets_minimum("610.74") is True
    assert driver_meets_minimum("572.65") is False
    assert driver_meets_minimum(None) is None
    assert driver_meets_minimum("") is None
    assert driver_meets_minimum("garbage") is None


def test_old_driver_produces_warning(tmp_path: Path):
    from dlss_combo.gpu import GpuInfo
    from dlss_combo import install as install_mod

    game = tmp_path / "game"
    game.mkdir()
    (game / "g.exe").write_bytes(b"MZ")
    kit = make_kit(tmp_path)

    fake = install_mod.detect_gpu
    install_mod.detect_gpu = lambda override=None: GpuInfo(
        vendor="nvidia", name="NVIDIA GeForce RTX 3070", arch="sm86",
        source="nvidia-smi", driver_version="572.65",
    )
    try:
        r = install_mod.install(game, kit, arch=None)
    finally:
        install_mod.detect_gpu = fake
    assert r.ok
    assert any("572.65" in w or "R580" in w for w in r.warnings)


# ---------- 缺口 2：--launch-swapper ----------

def test_launch_swapper_uses_kit_exe(tmp_path: Path):
    exe = tmp_path / "swapper" / "DLSS5-Swapper-portable.exe"
    exe.parent.mkdir(parents=True)
    exe.write_bytes(b"MZ")
    (tmp_path / "kit.json").write_text(
        json.dumps({"swapper": {"zip": "swapper/DLSS5-Swapper-portable.exe"}})
    )
    seen: list[Path] = []
    result = launch_swapper(tmp_path, spawn=seen.append)
    assert result == exe and seen == [exe]


def test_launch_swapper_missing_kit_raises(tmp_path: Path):
    with pytest.raises(FileNotFoundError):
        launch_swapper(tmp_path, spawn=lambda p: None)


def test_cli_launch_swapper_flag_wired(tmp_path: Path, monkeypatch, capsys):
    game = tmp_path / "game"
    game.mkdir()
    (game / "g.exe").write_bytes(b"MZ")
    kit = make_kit(tmp_path)
    import dlss_combo.fetch as fetch_mod

    called: list[Path] = []
    monkeypatch.setattr(
        fetch_mod, "launch_swapper", lambda kd, spawn=None: called.append(kd) or kit
    )
    rc = main(["install", str(game), "--kit-dir", str(kit), "--arch", "sm86", "--launch-swapper"])
    assert rc == 0 and called == [kit]
    assert "Swapper" in capsys.readouterr().out
