"""v0.1.0 发布验收 P1 回归：安装前原配置 → 安装 → 用户修改 → 重装/卸载。"""
from pathlib import Path

from dlss_combo.install import install
from dlss_combo.uninstall import uninstall
from tests.conftest import make_kit, rehash_kit


def _setup(tmp_path: Path):
    g = tmp_path / "game"
    g.mkdir()
    (g / "game.exe").write_bytes(b"MZ")
    (g / "dlssg_sm86.ini").write_text("; original user config\n", encoding="utf-8")
    kit = make_kit(tmp_path)
    install(g, kit, arch="sm86")
    # 用户在安装成功后手工修改 INI（外部修改变体）
    (g / "dlssg_sm86.ini").write_text(
        "; my tuned config after install\nPreset=B\n", encoding="utf-8"
    )
    return g, kit


def test_reinstall_preserves_user_modified_ini(tmp_path: Path):
    g, kit = _setup(tmp_path)
    (kit / "dlssg" / "310.9" / "version.dll").write_bytes(b"V9-new")
    rehash_kit(kit)
    r = install(g, kit, arch="sm86")  # 重装
    assert r.ok
    content = (g / "dlssg_sm86.ini").read_text(encoding="utf-8")
    assert content == "; my tuned config after install\nPreset=B\n"
    assert any("dlssg_sm86.ini" in w and "保留" in w for w in r.warnings)
    # 代理本体照常升级
    assert (g / "version.dll").read_bytes() == b"V9-new"


def test_uninstall_preserves_user_modified_ini_and_keeps_backup_copy(tmp_path: Path):
    g, kit = _setup(tmp_path)
    actions = uninstall(g)
    content = (g / "dlssg_sm86.ini").read_text(encoding="utf-8")
    assert content == "; my tuned config after install\nPreset=B\n"
    # 首次安装前的原配置不丢：以副本形式留在旁边
    backup_copy = g / "dlssg_sm86.ini.pre-existing"
    assert backup_copy.read_text(encoding="utf-8") == "; original user config\n"
    assert any("pre-existing" in a for a in actions)


def test_uninstall_still_restores_when_user_untouched(tmp_path: Path):
    """未被动过的常规路径回归：卸载仍还原首次安装前的原配置（不被本次改动破坏）。"""
    g = tmp_path / "game"
    g.mkdir()
    (g / "game.exe").write_bytes(b"MZ")
    (g / "dlssg_sm86.ini").write_text("; original user config\n", encoding="utf-8")
    kit = make_kit(tmp_path)
    install(g, kit, arch="sm86")
    uninstall(g)
    assert (g / "dlssg_sm86.ini").read_text(encoding="utf-8") == "; original user config\n"
