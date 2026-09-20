"""Read-only-to-project audit: all mutations stay in temporary fake game folders.

修复后语义（v0.1.2 起）：False 表示该缺陷场景已消除；全部为 False 即八个场景
均已修复。正式回归断言见 tests/test_review4.py。不下载、不执行真实 DLL。
"""
import importlib
import json
import os
from pathlib import Path
import sys
from tempfile import TemporaryDirectory
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[2]
sys.path[:0] = [str(ROOT / "src"), str(ROOT / "tests")]
from conftest import make_kit
from dlss_combo.doctor import doctor
from dlss_combo.fetch import fetch_kit, verify_kit
from dlss_combo.manifest import INI_NAME, MANIFEST_DIR
from dlss_combo.uninstall import uninstall

mod = importlib.import_module("dlss_combo.install")
results = {}

def case(name, check):
    with TemporaryDirectory(prefix="dlss-audit-") as td:
        root = Path(td)
        game = root / "game"
        game.mkdir()
        kit = make_kit(root)
        results[name] = bool(check(root, game, kit))

def install(game, kit):
    result = mod.install(game, kit, arch="sm86")
    assert result.ok, result.warnings

def rollback(root, game, kit):
    ini = game / INI_NAME
    ini.write_text("original user configuration")
    with patch.object(mod, "_atomic_copy", side_effect=OSError("simulated disk failure")):
        try:
            install(game, kit)
        except OSError:
            pass
        else:
            raise AssertionError("failure injection did not fire")
    return not ini.exists() and not (game / MANIFEST_DIR / "manifest.json").exists()

def side_copy(root, game, kit, symlink=False):
    ini = game / INI_NAME
    ini.write_text("original")
    install(game, kit)
    ini.write_text("edited after installation")
    side = game / (INI_NAME + ".pre-existing")
    sentinel = root / "outside-sentinel" if symlink else side
    sentinel.write_text("unrelated user file")
    if symlink:
        side.symlink_to(sentinel)
    uninstall(game)
    return sentinel.read_text() == "original" and ini.read_text() == "edited after installation"

def temp_link(root, game, kit):
    sentinel = root / "outside-sentinel"
    sentinel.write_text("unrelated user file")
    (game / (INI_NAME + ".dlsscombo-tmp")).symlink_to(sentinel)
    install(game, kit)
    return sentinel.read_text() != "unrelated user file"

def cleanup(root, game, kit):
    sentinel = game / "unrelated.dlsscombo-tmp"
    sentinel.write_text("not owned by this operation")
    install(game, kit)
    return not sentinel.exists()

def missing_backup(root, game, kit):
    ini = game / INI_NAME
    ini.write_text("original")
    install(game, kit)
    (game / MANIFEST_DIR / "backups" / (INI_NAME + ".pre.bak")).unlink()
    try:
        uninstall(game)
    except RuntimeError:
        return False  # 修复后：备份缺失即中止卸载且不删除任何文件
    return not ini.exists() and not (game / MANIFEST_DIR).exists()

def stale_log(root, game, kit):
    logs = game / "dlssg_sm86" / "logs"
    logs.mkdir(parents=True)
    older, newer = logs / "backend_old.jsonl", logs / "backend_new.jsonl"
    older.write_text('{"route":{"active":true}}\n')
    newer.write_text('{"event":"new session started"}\n')
    os.utime(older, (100, 100))
    os.utime(newer, (200, 200))
    return doctor(game).route_active is True

def refresh_failure(root, game, kit):
    assert not verify_kit(kit)
    def fetch(url):
        if url.endswith("commits/main"):
            return b'{"sha":"newcommit"}'
        if url.endswith("version.dll"):
            return b"new version"
        raise OSError("simulated network interruption")
    try:
        fetch_kit(kit, refresh=True, fetch_bytes=fetch)
    except OSError:
        pass
    else:
        raise AssertionError("failure injection did not fire")
    return any("hash mismatch" in p for p in verify_kit(kit))

case("first_install_failure_loses_live_original_ini", rollback)
case("uninstall_overwrites_existing_side_copy", side_copy)
case("uninstall_side_copy_symlink_overwrites_outside_file", lambda *a: side_copy(*a, symlink=True))
case("install_predictable_temp_symlink_overwrites_outside_file", temp_link)
case("successful_install_deletes_unowned_temp_file", cleanup)
case("uninstall_silently_discards_state_when_backup_missing", missing_backup)
case("doctor_uses_old_success_when_new_session_has_no_route", stale_log)
case("interrupted_refresh_breaks_previously_valid_kit", refresh_failure)
print(json.dumps(results, indent=2))
# 修复后：任何 true 都表示该缺陷场景仍然存在
assert not any(results.values()), "STILL PRESENT: " + str([k for k, v in results.items() if v])
