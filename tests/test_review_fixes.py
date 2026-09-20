"""审查修复的回归测试：锁定两条安全不变量。"""
import json
from pathlib import Path

import pytest

from dlss_combo.install import INI_NAME, install
from tests.conftest import make_kit


def test_reinstall_never_deletes_paths_outside_proxy_scope(tmp_path: Path):
    """重要问题 1 回归（fail-closed 强化）：manifest 被篡改时直接拒绝安装。"""
    game = tmp_path / "game"
    game.mkdir()
    (game / "game.exe").write_bytes(b"MZ")
    kit = make_kit(tmp_path)
    install(game, kit, arch="sm86")
    precious = game / "reshade-shaders"
    precious.mkdir()
    # 恶意/误操作的 manifest：把第三方路径塞进 files
    m_path = game / ".dlss-combo" / "manifest.json"
    data = json.loads(m_path.read_text())
    data["files"].append({"path": "reshade-shaders", "sha256": "x", "origin": "kit"})
    data["files"].append({"path": "game.exe", "sha256": "x", "origin": "kit"})
    m_path.write_text(json.dumps(data))

    r = install(game, kit, arch="sm86")  # 触发重装路径 → fail-closed
    assert not r.ok  # 非法 manifest：拒绝而非猜测性操作
    assert any("manifest" in w for w in r.warnings)
    assert precious.is_dir()           # 第三方目录未被动
    assert (game / "game.exe").exists()  # 游戏 exe 未被动


def test_rollback_restores_deleted_own_proxy(tmp_path: Path, monkeypatch):
    """重要问题 2 回归：写盘阶段抛异常时，已删的旧代理须从备份还原。"""
    game = tmp_path / "game"
    game.mkdir()
    (game / "game.exe").write_bytes(b"MZ")
    kit = make_kit(tmp_path)
    install(game, kit, arch="sm86")  # 第一代安装：version.dll = b"V9"

    # 第二代安装中段炸掉：让 ini 写盘成功、代理复制抛异常
    from dlss_combo import install as install_mod

    real_copy = install_mod.shutil.copy2

    def boom(src, dst, *a, **kw):
        # 只在 kit→游戏 的代理复制时爆炸；备份/还原的拷贝（源以 .bak 结尾）放行
        if str(src).endswith("version.dll"):
            raise OSError("disk full")
        return real_copy(src, dst, *a, **kw)

    monkeypatch.setattr(install_mod.shutil, "copy2", boom)
    with pytest.raises(OSError):
        install(game, kit, arch="sm86")
    monkeypatch.setattr(install_mod.shutil, "copy2", real_copy)

    # 旧代理从备份回来了（而不是只剩 backups 里的副本）
    assert (game / "version.dll").read_bytes() == b"V9"
