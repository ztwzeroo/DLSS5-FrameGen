"""v0.1.1 独立复核（docs/reviews/2026-09-20-v0.1.1-independent-review.md）
八个复现场景的正式回归 + R1 验收要求的故障注入扩展。"""
import json
import os
from pathlib import Path

import pytest

from dlss_combo import install as install_mod
from dlss_combo.doctor import doctor
from dlss_combo.fetch import fetch_kit, verify_kit
from dlss_combo.install import INI_NAME, MANIFEST_DIR, install
from dlss_combo.manifest import Manifest
from dlss_combo.uninstall import uninstall
from tests.conftest import make_kit

USER_INI = "; original user configuration\n"


def _game_with_user_ini(tmp_path: Path) -> Path:
    g = tmp_path / "game"
    g.mkdir()
    (g / "game.exe").write_bytes(b"MZ")
    (g / INI_NAME).write_text(USER_INI, encoding="utf-8")
    return g


# ---------- R1：首次安装各故障点都还原用户 INI ----------

def test_dll_failure_restores_user_ini(tmp_path: Path, monkeypatch):
    g = _game_with_user_ini(tmp_path)
    kit = make_kit(tmp_path)
    real_copy = install_mod.shutil.copy2

    def broken(src, dst, *a, **kw):
        if str(src).endswith("version.dll"):
            raise OSError("disk full")
        return real_copy(src, dst, *a, **kw)

    monkeypatch.setattr(install_mod.shutil, "copy2", broken)
    with pytest.raises(OSError):
        install(g, kit, arch="sm86")
    assert (g / INI_NAME).read_text(encoding="utf-8") == USER_INI
    assert not (g / MANIFEST_DIR / "manifest.json").exists()


def test_manifest_failure_restores_user_ini(tmp_path: Path, monkeypatch):
    g = _game_with_user_ini(tmp_path)
    kit = make_kit(tmp_path)
    monkeypatch.setattr(Manifest, "save", lambda self, gd: (_ for _ in ()).throw(OSError("manifest write failed")))
    with pytest.raises(OSError):
        install(g, kit, arch="sm86")
    assert (g / INI_NAME).read_text(encoding="utf-8") == USER_INI
    assert not (g / "version.dll").exists()


def test_backup_write_failure_leaves_ini_untouched(tmp_path: Path, monkeypatch):
    g = _game_with_user_ini(tmp_path)
    kit = make_kit(tmp_path)
    real_copy = install_mod.shutil.copy2
    ini_abs = str(g / INI_NAME)

    def broken(src, dst, *a, **kw):
        if str(src) == ini_abs:  # 首次备份用户 INI 那一步失败
            raise OSError("backup volume error")
        return real_copy(src, dst, *a, **kw)

    monkeypatch.setattr(install_mod.shutil, "copy2", broken)
    with pytest.raises(OSError):
        install(g, kit, arch="sm86")
    assert (g / INI_NAME).read_text(encoding="utf-8") == USER_INI


def test_reinstall_failure_restores_previous_state(tmp_path: Path, monkeypatch):
    g = _game_with_user_ini(tmp_path)
    kit = make_kit(tmp_path)
    install(g, kit, arch="sm86")
    ours_ini = (g / INI_NAME).read_text(encoding="utf-8")
    real_copy = install_mod.shutil.copy2

    def broken(src, dst, *a, **kw):
        if str(src).endswith("version.dll"):
            raise OSError("disk full")
        return real_copy(src, dst, *a, **kw)

    monkeypatch.setattr(install_mod.shutil, "copy2", broken)
    with pytest.raises(OSError):
        install(g, kit, arch="sm86")
    # 上一代的完好状态被完整还原
    assert (g / "version.dll").read_bytes() == b"V9"
    assert (g / INI_NAME).read_text(encoding="utf-8") == ours_ini
    m = Manifest.load(g)
    assert not m.verify(g)


# ---------- R2：卸载另存副本绝不覆盖任何现有文件/链接 ----------

def _user_modified_ini_game(tmp_path: Path) -> Path:
    g = _game_with_user_ini(tmp_path)
    kit = make_kit(tmp_path)
    install(g, kit, arch="sm86")
    (g / INI_NAME).write_text("; edited after installation\n", encoding="utf-8")
    return g


def test_side_copy_never_overwrites_existing_file(tmp_path: Path):
    g = _user_modified_ini_game(tmp_path)
    side = g / (INI_NAME + ".pre-existing")
    side.write_text("unrelated user file", encoding="utf-8")
    uninstall(g)
    assert side.read_text(encoding="utf-8") == "unrelated user file"
    numbered = g / (INI_NAME + ".pre-existing.1")
    assert numbered.read_text(encoding="utf-8") == USER_INI.strip() + "\n"


def test_side_copy_skips_symlink_escape(tmp_path: Path):
    g = _user_modified_ini_game(tmp_path)
    sentinel = tmp_path / "outside-sentinel"
    sentinel.write_text("unrelated user file", encoding="utf-8")
    side = g / (INI_NAME + ".pre-existing")
    side.symlink_to(sentinel)
    uninstall(g)
    assert sentinel.read_text(encoding="utf-8") == "unrelated user file"
    assert (g / (INI_NAME + ".pre-existing.1")).exists()


# ---------- R3：随机排他临时文件 + 只清理本操作登记的路径 ----------

def test_predictable_temp_symlink_is_inert(tmp_path: Path):
    g = _game_with_user_ini(tmp_path)
    kit = make_kit(tmp_path)
    sentinel = tmp_path / "outside-sentinel"
    sentinel.write_text("unrelated user file", encoding="utf-8")
    (g / (INI_NAME + ".dlsscombo-tmp")).symlink_to(sentinel)
    r = install(g, kit, arch="sm86")
    assert r.ok
    assert sentinel.read_text(encoding="utf-8") == "unrelated user file"


def test_unowned_temp_file_survives_install(tmp_path: Path):
    g = _game_with_user_ini(tmp_path)
    kit = make_kit(tmp_path)
    unowned = g / "unrelated.dlsscombo-tmp"
    unowned.write_text("not owned by this operation", encoding="utf-8")
    install(g, kit, arch="sm86")
    assert unowned.read_text(encoding="utf-8") == "not owned by this operation"
    # 成功后我们自己的临时件也不残留
    leftovers = [p.name for p in g.iterdir() if p.name.startswith(".dlsscombo-")]
    assert leftovers == []


def test_our_temps_cleaned_on_failure(tmp_path: Path, monkeypatch):
    g = _game_with_user_ini(tmp_path)
    kit = make_kit(tmp_path)
    real_copy = install_mod.shutil.copy2

    def broken(src, dst, *a, **kw):
        if str(src).endswith("version.dll"):
            raise OSError("disk full")
        return real_copy(src, dst, *a, **kw)

    monkeypatch.setattr(install_mod.shutil, "copy2", broken)
    with pytest.raises(OSError):
        install(g, kit, arch="sm86")
    leftovers = [p.name for p in g.iterdir() if ".dlsscombo-" in p.name]
    assert leftovers == []


# ---------- R5：备份缺失 → 拒绝删除，状态保留 ----------

def test_missing_preexisting_backup_aborts_uninstall(tmp_path: Path):
    g = _game_with_user_ini(tmp_path)
    kit = make_kit(tmp_path)
    install(g, kit, arch="sm86")
    (g / MANIFEST_DIR / "backups" / (INI_NAME + ".pre.bak")).unlink()
    with pytest.raises(RuntimeError, match="备份"):
        uninstall(g)
    # 未删除任何东西
    assert (g / "version.dll").exists()
    assert (g / INI_NAME).exists()
    assert (g / MANIFEST_DIR).exists()


# ---------- R6：doctor 以最新会话为诊断范围 ----------

def test_doctor_stale_success_is_not_reported_as_current(tmp_path: Path):
    logs = tmp_path / "dlssg_sm86" / "logs"
    logs.mkdir(parents=True)
    older, newer = logs / "backend_old.jsonl", logs / "backend_new.jsonl"
    older.write_text('{"route":{"active":true}}\n', encoding="utf-8")
    newer.write_text('{"event":"new session started"}\n', encoding="utf-8")
    os.utime(older, (100, 100))
    os.utime(newer, (200, 200))
    rep = doctor(tmp_path)
    assert rep.route_active is None
    assert not any("OK: dlssg 插帧路由已生效" in l for l in rep.lines)
    assert any("未验证" in l or "无 route" in l for l in rep.lines)
    assert any("历史" in l and "backend_old" in l for l in rep.lines)


# ---------- R7：刷新中断不破坏可用 kit ----------

def test_interrupted_refresh_keeps_old_kit_valid(tmp_path: Path):
    kit = make_kit(tmp_path)
    meta_before = (kit / "kit.json").read_text(encoding="utf-8")
    assert verify_kit(kit) == []

    def fetch(url: str) -> bytes:
        if url.endswith("commits/main"):
            return b'{"sha":"newcommit"}'
        if url.endswith("version.dll"):
            return b"new version"
        raise OSError("simulated network interruption")

    with pytest.raises(OSError):
        fetch_kit(kit, refresh=True, fetch_bytes=fetch)
    assert verify_kit(kit) == []  # 旧 kit 完好
    assert (kit / "kit.json").read_text(encoding="utf-8") == meta_before
    assert not list(kit.glob(".staging*"))  # 无残留 staging
