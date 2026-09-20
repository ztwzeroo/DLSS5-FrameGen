import json
from pathlib import Path

import pytest

from dlss_combo.install import install
from tests.conftest import rehash_kit
from dlss_combo.uninstall import uninstall
from tests.conftest import rehash_kit


def test_uninstall_restores_clean_state(game: Path, kit: Path):
    (game / "version.dll").write_bytes(b"someone-else")  # 第三方文件
    install(game, kit, arch="sm86")  # version.dll 被占 → 自动选 winmm
    actions = uninstall(game)
    assert not (game / "winmm.dll").exists()
    assert not (game / "dlssg_sm86.ini").exists()
    assert not (game / ".dlss-combo").exists()
    # 第三方文件原封不动
    assert (game / "version.dll").read_bytes() == b"someone-else"
    assert (game / "game.exe").exists()
    assert actions


def test_uninstall_restores_backup_of_foreign_file(tmp_path: Path, kit: Path):
    # 历史/未来的"覆盖过第三方文件"场景：manifest 里存在备份记录时应还原
    game = tmp_path / "game"
    game.mkdir()
    (game / "version.dll").write_bytes(b"orig")
    install(game, kit, arch="sm86")  # version.dll 被第三方占用 → 装 winmm
    m_path = game / ".dlss-combo" / "manifest.json"
    data = json.loads(m_path.read_text())
    backup = game / ".dlss-combo" / "backups" / "version.dll.bak"
    backup.parent.mkdir(parents=True, exist_ok=True)
    backup.write_bytes(b"orig-restored")
    data["backups"] = [
        {"original": "version.dll", "saved_to": ".dlss-combo/backups/version.dll.bak"}
    ]
    m_path.write_text(json.dumps(data))
    actions = uninstall(game)
    # 新语义（发布验收 P1）：在场的外部文件不被覆盖，原配置另存副本
    assert (game / "version.dll").read_bytes() == b"orig"
    assert (game / "version.dll.pre-existing").read_bytes() == b"orig-restored"
    assert any("pre-existing" in a for a in actions)


def test_uninstall_after_reinstall_leaves_no_stale_proxy(game: Path, kit: Path):
    install(game, kit, arch="sm86")
    (kit / "dlssg" / "310.9" / "version.dll").write_bytes(b"V9-new")
    rehash_kit(kit)
    install(game, kit, arch="sm86")  # 重装：旧 version.dll 进备份
    uninstall(game)
    assert not (game / "version.dll").exists()  # 备份是我们自己的旧件，不还原
    assert not any(game.glob("*.dll"))


def test_uninstall_without_manifest_raises(tmp_path: Path):
    with pytest.raises(FileNotFoundError):
        uninstall(tmp_path)
