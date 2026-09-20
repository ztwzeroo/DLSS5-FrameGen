from pathlib import Path

from dlss_combo.scan import scan_game_dir


def test_clean_dir(tmp_path: Path):
    s = scan_game_dir(tmp_path)
    assert s.existing_proxies == {}
    assert not any([s.reshade, s.optiscaler, s.renodx, s.feeder, s.has_our_install])


def test_foreign_version_dll(tmp_path: Path):
    (tmp_path / "version.dll").write_bytes(b"x")
    s = scan_game_dir(tmp_path)
    assert s.existing_proxies == {"version.dll": "foreign"}


def test_ours_marker(tmp_path: Path):
    (tmp_path / "version.dll").write_bytes(b"x")
    s = scan_game_dir(tmp_path, our_files={"version.dll"})
    assert s.existing_proxies == {"version.dll": "ours"}
    assert s.has_our_install


def test_reshade_detected_by_shaders_dir(tmp_path: Path):
    shaders = tmp_path / "reshade-shaders"
    (shaders / "SweetFX").mkdir(parents=True)
    (shaders / "SweetFX" / "f.fx").write_text("// shader\n")
    (tmp_path / "dxgi.dll").write_bytes(b"x")
    s = scan_game_dir(tmp_path)
    assert s.reshade
    assert s.existing_proxies["dxgi.dll"] == "foreign"


def test_empty_reshade_shaders_dir_is_not_reshade(tmp_path: Path):
    (tmp_path / "reshade-shaders").mkdir()
    (tmp_path / "dxgi.dll").write_bytes(b"x")
    assert not scan_game_dir(tmp_path).reshade


def test_reshade_detected_by_ini_and_dxgi(tmp_path: Path):
    (tmp_path / "dxgi.dll").write_bytes(b"x")
    (tmp_path / "ReShade.ini").write_text("[GENERAL]\n")
    assert scan_game_dir(tmp_path).reshade


def test_optiscaler_by_ini(tmp_path: Path):
    (tmp_path / "OptiScaler.ini").write_text("[General]\n")
    assert scan_game_dir(tmp_path).optiscaler


def test_optiscaler_by_folder(tmp_path: Path):
    (tmp_path / "OptiScaler").mkdir()
    assert scan_game_dir(tmp_path).optiscaler


def test_renodx_and_feeder_markers(tmp_path: Path):
    (tmp_path / "renoDX_somegame.dll").write_bytes(b"x")
    (tmp_path / "dlss5-feeder.addon").write_bytes(b"x")
    s = scan_game_dir(tmp_path)
    assert s.renodx and s.feeder
