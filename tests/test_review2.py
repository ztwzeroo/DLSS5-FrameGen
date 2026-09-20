"""外部审查（docs/reviews/2026-09-20-project-review.md）9 个复现场景的正式回归：
断言的是修复后的行为（原复现脚本断言的是缺陷存在）。"""
import hashlib
import json
from pathlib import Path

import pytest

from dlss_combo.doctor import _parse_route_active, doctor
from dlss_combo.fetch import fetch_kit, launch_swapper, verify_kit
from dlss_combo.install import install
from dlss_combo.manifest import Manifest
from dlss_combo.proxy_select import PROXY_CANDIDATES
from dlss_combo.uninstall import uninstall
from tests.conftest import make_kit, rehash_kit

# ---------- A. 卸载越界 ----------

def test_uninstall_rejects_traversal_manifest(tmp_path: Path):
    g = tmp_path / "game"
    g.mkdir()
    outside = tmp_path / "outside-sentinel.txt"
    outside.write_text("keep")
    m = Manifest()
    m.record_file("../outside-sentinel.txt", Manifest.sha256_of(outside), "kit")
    m.save(g)
    with pytest.raises(ValueError, match="manifest"):
        uninstall(g)
    assert outside.exists() and outside.read_text() == "keep"


def test_uninstall_rejects_absolute_path_manifest(tmp_path: Path):
    g = tmp_path / "game"
    g.mkdir()
    outside = tmp_path / "abs-sentinel.txt"
    outside.write_text("keep")
    m = Manifest()
    m.record_file(str(outside), Manifest.sha256_of(outside), "kit")
    m.save(g)
    with pytest.raises(ValueError):
        uninstall(g)
    assert outside.exists()


def test_uninstall_rejects_backup_escape(tmp_path: Path):
    g = tmp_path / "game"
    g.mkdir()
    target = tmp_path / "escape-target.dll"
    target.write_bytes(b"precious")
    bak = g / ".dlss-combo" / "backups" / "b.bak"
    bak.parent.mkdir(parents=True)
    bak.write_bytes(b"evil")
    m = Manifest()
    m.record_file("version.dll", "0" * 64, "kit")
    m.record_backup("version.dll", "../../escape-target.dll")
    m.save(g)
    with pytest.raises(ValueError):
        uninstall(g)
    assert target.read_bytes() == b"precious"


def test_uninstall_rejects_unknown_manifest_version(tmp_path: Path):
    g = tmp_path / "game"
    g.mkdir()
    (g / "version.dll").write_bytes(b"x")
    m = Manifest()
    m.record_file("version.dll", "0" * 64, "kit")
    m.save(g)
    p = g / ".dlss-combo" / "manifest.json"
    data = json.loads(p.read_text())
    data["version"] = 99
    p.write_text(json.dumps(data))
    with pytest.raises(ValueError, match="version"):
        uninstall(g)
    assert (g / "version.dll").exists()


# ---------- B. 外部替换的 DLL 不得被覆盖/删除 ----------

def test_replaced_dll_survives_reinstall_and_uninstall(tmp_path: Path):
    g = tmp_path / "game"
    g.mkdir()
    (g / "game.exe").write_bytes(b"MZ")
    kit = make_kit(tmp_path)
    install(g, kit, arch="sm86")
    (g / "version.dll").write_bytes(b"new third party mod")
    r = install(g, kit, arch="sm86")  # 重装
    assert (g / "version.dll").read_bytes() == b"new third party mod"
    assert any("外部修改" in w or "保留" in w for w in r.warnings)
    uninstall(g)
    assert (g / "version.dll").read_bytes() == b"new third party mod"


# ---------- C. 首次安装前的外来 INI 跨安装/重装/卸载保持 ----------

def test_preexisting_ini_preserved_across_lifecycle(tmp_path: Path):
    g = tmp_path / "game"
    g.mkdir()
    (g / "game.exe").write_bytes(b"MZ")
    kit = make_kit(tmp_path)
    original_ini = "; original custom settings\nPreset=B\n"
    (g / "dlssg_sm86.ini").write_text(original_ini)
    install(g, kit, arch="sm86")
    (kit / "dlssg" / "310.9" / "version.dll").write_bytes(b"V9b")
    rehash_kit(kit)
    install(g, kit, arch="sm86")  # 重装升级
    uninstall(g)
    assert (g / "dlssg_sm86.ini").read_text() == original_ini


# ---------- D. 校验强度 ----------

def test_verify_kit_fails_on_missing_checksums(tmp_path: Path):
    kit = make_kit(tmp_path)
    meta_path = kit / "kit.json"
    original = meta_path.read_text()
    meta = json.loads(original)
    meta["files"] = {}
    meta_path.write_text(json.dumps(meta))
    problems = verify_kit(kit)
    assert any("missing checksum" in p for p in problems)
    meta_path.write_text(original)


def test_verify_kit_fails_on_bad_hash_format(tmp_path: Path):
    kit = make_kit(tmp_path)
    meta_path = kit / "kit.json"
    meta = json.loads(meta_path.read_text())
    key = next(iter(meta["files"]))
    meta["files"][key] = "zz"
    meta_path.write_text(json.dumps(meta))
    assert any(key in p for p in verify_kit(kit))


def test_launch_swapper_verifies_hash_before_spawn(tmp_path: Path):
    exe = tmp_path / "swapper" / "portable.exe"
    exe.parent.mkdir(parents=True)
    exe.write_bytes(b"original exe")
    (tmp_path / "kit.json").write_text(
        json.dumps(
            {"swapper": {"zip": "swapper/portable.exe", "tag": "t",
                         "sha256": hashlib.sha256(b"original exe").hexdigest()}}
        )
    )
    exe.write_bytes(b"modified exe")
    launched: list[Path] = []
    with pytest.raises(RuntimeError, match="hash"):
        launch_swapper(tmp_path, spawn=launched.append)
    assert launched == []


def test_launch_swapper_refuses_zip(tmp_path: Path):
    z = tmp_path / "swapper" / "portable.zip"
    z.parent.mkdir(parents=True)
    z.write_bytes(b"PK")
    (tmp_path / "kit.json").write_text(
        json.dumps({"swapper": {"zip": "swapper/portable.zip",
                                "sha256": hashlib.sha256(b"PK").hexdigest()}})
    )
    with pytest.raises(RuntimeError, match="zip"):
        launch_swapper(tmp_path, spawn=lambda p: None)


# ---------- E. 部分写入故障：目标文件不得损坏 ----------

def test_partial_copy_failure_leaves_old_dll_intact(tmp_path: Path, monkeypatch):
    g = tmp_path / "game"
    g.mkdir()
    (g / "game.exe").write_bytes(b"MZ")
    kit = make_kit(tmp_path)
    install(g, kit, arch="sm86")  # version.dll = V9

    from dlss_combo import install as install_mod

    real_copy = install_mod.shutil.copy2

    def broken_copy(src, dst, *a, **kw):
        if str(src).endswith("version.dll") and str(dst).endswith(".dlsscombo-tmp"):
            Path(dst).write_bytes(b"PARTIAL")
            raise OSError("disk full mid-copy")
        return real_copy(src, dst, *a, **kw)

    monkeypatch.setattr(install_mod.shutil, "copy2", broken_copy)
    (kit / "dlssg" / "310.9" / "version.dll").write_bytes(b"V9-new")
    rehash_kit(kit)
    with pytest.raises(OSError):
        install(g, kit, arch="sm86")

    assert (g / "version.dll").read_bytes() == b"V9"
    assert not list(g.glob("*.dlsscombo-tmp"))  # 临时文件被清理


# ---------- F. kit 事务性 ----------

def _fake_net(files: dict[str, bytes], commit: bytes = b'{"sha":"audit-commit"}'):
    def fetch_bytes(url: str) -> bytes:
        for key in sorted(files, key=len, reverse=True):
            if url.endswith(key):
                return files[key]
        if url.endswith("commits/main"):
            return commit
        raise RuntimeError(f"unexpected {url}")

    return fetch_bytes


def test_fetch_refresh_preserves_swapper_meta(tmp_path: Path):
    files = {"version.dll": b"d1", "dlssg_sm86.ini": b"[G]",
             **{f"alternatives/{n}.dll": n.encode() for n in
                ["winmm", "d3d12", "dbghelp", "dinput8", "dxgi"]}}
    fetch_kit(tmp_path, fetch_bytes=_fake_net(files))
    meta_path = tmp_path / "kit.json"
    meta = json.loads(meta_path.read_text())
    meta["swapper"] = {"zip": "swapper/p.exe", "tag": "v1",
                       "sha256": "0" * 64, "checksum_source": "self"}
    meta_path.write_text(json.dumps(meta))
    fetch_kit(tmp_path, refresh=True, fetch_bytes=_fake_net(
        {**files, "version.dll": b"d2"},
        commit=b'{"sha":"next-commit"}'))
    meta2 = json.loads(meta_path.read_text())
    assert meta2["swapper"]["tag"] == "v1"
    assert (tmp_path / "dlssg" / "310.9" / "version.dll").read_bytes() == b"d2"


def test_fetch_records_per_runtime_commits(tmp_path: Path):
    files9 = {"version.dll": b"d9", "dlssg_sm86.ini": b"[G]",
              **{f"alternatives/{n}.dll": n.encode() for n in
                 ["winmm", "d3d12", "dbghelp", "dinput8", "dxgi"]}}
    files1 = {"310.1/version.dll": b"d1",
              **{f"310.1/alternatives/{n}.dll": n.encode() for n in
                 ["winmm", "d3d12", "dbghelp", "dinput8", "dxgi"]}}
    fetch_kit(tmp_path, fetch_bytes=_fake_net(files9, commit=b'{"sha":"commit-9"}'))
    fetch_kit(tmp_path, runtime="310.1",
              fetch_bytes=_fake_net({**files9, **files1}, commit=b'{"sha":"commit-1"}'))
    meta = json.loads((tmp_path / "kit.json").read_text())
    assert meta["dlssg_commits"] == {"310.9": "commit-9", "310.1": "commit-1"}


def test_cache_hit_revalidates_and_refetches_corrupt_file(tmp_path: Path):
    files = {"version.dll": b"d1", "dlssg_sm86.ini": b"[G]",
             **{f"alternatives/{n}.dll": n.encode() for n in
                ["winmm", "d3d12", "dbghelp", "dinput8", "dxgi"]}}
    calls: list[str] = []
    base = _fake_net(files)

    def counting(url: str) -> bytes:
        calls.append(url)
        return base(url)

    fetch_kit(tmp_path, fetch_bytes=counting)
    n_after_first = len(calls)
    (tmp_path / "dlssg" / "310.9" / "version.dll").write_bytes(b"corrupted")
    kit = fetch_kit(tmp_path, fetch_bytes=counting)  # 缓存命中但发现损坏 → 重下
    assert (tmp_path / "dlssg" / "310.9" / "version.dll").read_bytes() == b"d1"
    assert len(calls) > n_after_first


# ---------- G. doctor 准确性 ----------

def test_parse_route_active_last_event_wins():
    text = '{"route":{"active":true}}\n{"route":{"active":false}}\n'
    assert _parse_route_active(text) is False


def test_parse_route_active_strict_booleans():
    assert _parse_route_active('{"route":{"active":"false"}}\n') is None
    assert _parse_route_active('[1,2,3]\n') is None
    assert _parse_route_active('not json\n{"route":{"active":true}}\n') is True


def test_doctor_empty_reshade_folder_is_not_dlss5(tmp_path: Path):
    (tmp_path / "reshade-shaders").mkdir()
    rep = doctor(tmp_path)
    assert not any("OK: 检测到 DLSS 5" in l for l in rep.lines)


def test_doctor_report_problems_and_cli_exit_code(tmp_path: Path, game: Path, kit: Path, capsys):
    from dlss_combo.cli import main

    install(game, kit, arch="sm86")
    (game / "version.dll").write_bytes(b"tampered")
    assert doctor(game).has_problems
    assert main(["doctor", str(game)]) == 1


def test_doctor_route_false_nonzero_exit(game: Path, kit: Path, capsys):
    from dlss_combo.cli import main

    install(game, kit, arch="sm86")
    logdir = game / "dlssg_sm86" / "logs"
    logdir.mkdir(parents=True)
    (logdir / "backend_1.jsonl").write_text('{"route":{"active":false}}\n')
    assert doctor(game).has_problems
    assert main(["doctor", str(game)]) == 1


# ---------- H. 代理顺序与 --proxy ----------

def test_proxy_order_puts_d3d12_after_all_tool_proxies():
    assert PROXY_CANDIDATES == [
        "version.dll", "winmm.dll", "dbghelp.dll", "dinput8.dll",
        "d3d12.dll", "dxgi.dll",
    ]


def test_install_with_explicit_proxy(tmp_path: Path):
    g = tmp_path / "game"
    g.mkdir()
    (g / "g.exe").write_bytes(b"MZ")
    kit = make_kit(tmp_path)
    r = install(g, kit, arch="sm86", proxy="winmm.dll")
    assert r.ok and r.proxy_name == "winmm.dll"
    assert (g / "winmm.dll").exists() and not (g / "version.dll").exists()


def test_install_rejects_foreign_explicit_proxy(tmp_path: Path):
    g = tmp_path / "game"
    g.mkdir()
    (g / "g.exe").write_bytes(b"MZ")
    (g / "winmm.dll").write_bytes(b"foreign")
    kit = make_kit(tmp_path)
    r = install(g, kit, arch="sm86", proxy="winmm.dll")
    assert not r.ok


# ---------- I. 预检一致性 ----------

def test_3101_rejects_6x(tmp_path: Path):
    g = tmp_path / "game"
    g.mkdir()
    (g / "g.exe").write_bytes(b"MZ")
    kit = make_kit(tmp_path)
    r = install(g, kit, arch="sm86", runtime="310.1", mfg="6x")
    assert not r.ok
    assert any("6x" in w or "4X" in w for w in r.warnings)


def test_arch_override_still_reports_old_driver(tmp_path: Path, monkeypatch):
    g = tmp_path / "game"
    g.mkdir()
    (g / "g.exe").write_bytes(b"MZ")
    kit = make_kit(tmp_path)
    from dlss_combo import install as install_mod

    monkeypatch.setattr(
        install_mod, "detect_gpu",
        lambda override=None: __import__("dlss_combo.gpu", fromlist=["GpuInfo"]).GpuInfo(
            vendor="nvidia", name="NVIDIA GeForce RTX 3070", arch="sm86",
            source="nvidia-smi", driver_version="572.65"),
    )
    r = install_mod.install(g, kit, arch=None)
    assert r.ok and any("R580" in w for w in r.warnings)


# ---------- 复现场景综合：跨生命周期 ----------

def test_full_lifecycle_never_touches_third_party(tmp_path: Path):
    g = tmp_path / "game"
    g.mkdir()
    (g / "game.exe").write_bytes(b"MZ")
    (g / "reshade-shaders" / "Shaders").mkdir(parents=True)  # 非空 = 真 ReShade
    (g / "dxgi.dll").write_bytes(b"reshade")
    original_ini = "; my hand-tuned config\n"
    (g / "dlssg_sm86.ini").write_text(original_ini)
    kit = make_kit(tmp_path)

    install(g, kit, arch="sm86")
    assert (g / "dxgi.dll").read_bytes() == b"reshade"
    (kit / "dlssg" / "310.9" / "version.dll").write_bytes(b"V9-new")
    rehash_kit(kit)
    install(g, kit, arch="sm86")
    uninstall(g)
    assert (g / "dxgi.dll").read_bytes() == b"reshade"
    assert (g / "dlssg_sm86.ini").read_text() == original_ini
    assert sorted(p.name for p in g.glob("*.dll")) == ["dxgi.dll"]
