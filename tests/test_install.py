import json
from pathlib import Path

from dlss_combo.install import install


def test_fresh_install_uses_version_dll(game: Path, kit: Path):
    r = install(game, kit, arch="sm86")
    assert r.ok and r.proxy_name == "version.dll"
    assert (game / "version.dll").read_bytes() == b"V9"
    ini = (game / "dlssg_sm86.ini").read_text()
    assert "MaxGeneratedFrames=3" in ini
    m = json.loads((game / ".dlss-combo" / "manifest.json").read_text())
    assert m["dlssg"]["proxy_name"] == "version.dll"
    assert m["dlssg"]["commit"] == "c0ffee"
    assert {f["path"] for f in m["files"]} == {"version.dll", "dlssg_sm86.ini"}


def test_foreign_version_dll_gets_winmm_no_overwrite(game: Path, kit: Path):
    (game / "version.dll").write_bytes(b"someone-else")
    r = install(game, kit, arch="sm86")
    assert r.ok and r.proxy_name == "winmm.dll"
    assert (game / "version.dll").read_bytes() == b"someone-else"
    assert (game / "winmm.dll").read_bytes() == b"winmm"


def test_reshade_dxgi_present_prefers_version_dll(game: Path, kit: Path):
    (game / "reshade-shaders").mkdir()
    (game / "dxgi.dll").write_bytes(b"reshade")
    r = install(game, kit, arch="sm86")
    assert r.proxy_name == "version.dll"
    assert any(
        "ReShade" in w or "DLSS 5" in w for w in r.warnings + r.guidance
    )


def test_unsupported_arch_needs_override(game: Path, kit: Path):
    r = install(game, kit, arch="sm120")
    assert not r.ok
    assert any("sm120" in w for w in r.warnings)


def test_all_proxies_occupied_fails(game: Path, kit: Path):
    for n in ["version", "winmm", "d3d12", "dbghelp", "dinput8", "dxgi"]:
        (game / f"{n}.dll").write_bytes(b"x")
    r = install(game, kit, arch="sm86", allow_dxgi=True)
    assert not r.ok and r.proxy_name is None


def test_reinstall_upgrades_and_keeps_single_proxy(game: Path, kit: Path):
    assert install(game, kit, arch="sm86").ok
    (kit / "dlssg" / "310.9" / "version.dll").write_bytes(b"V9-new")
    r = install(game, kit, arch="sm86")
    assert r.ok and r.proxy_name == "version.dll"
    assert (game / "version.dll").read_bytes() == b"V9-new"
    assert sorted(p.name for p in game.glob("*.dll")) == ["version.dll"]


def test_6x_writes_maxframes_5(game: Path, kit: Path):
    r = install(game, kit, arch="sm86", mfg="6x", tier=2)
    assert r.ok
    assert "MaxGeneratedFrames=5" in (game / "dlssg_sm86.ini").read_text()
    assert "Optimized=2" in (game / "dlssg_sm86.ini").read_text()


def test_missing_dlss5_layer_gets_guidance(game: Path, kit: Path):
    r = install(game, kit, arch="sm86")
    assert any("DLSS5-Swapper" in g for g in r.guidance)


def test_missing_kit_files_fail_closed(game: Path, kit: Path):
    (kit / "dlssg" / "310.9" / "version.dll").unlink()
    r = install(game, kit, arch="sm86")
    assert not r.ok
