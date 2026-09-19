"""卸载：按 manifest 删除本工具文件、还原第三方备份、清理 .dlss-combo。"""
import shutil
from pathlib import Path

from .manifest import MANIFEST_DIR, Manifest


def uninstall(game_dir: Path) -> list[str]:
    """还原到安装前状态；无 manifest 时抛 FileNotFoundError。

    备份还原规则：只还原"当前不属于本工具"的 original——重装路径产生的备份
    是我们自己的旧代理，还原它反而会留下残留；真正的第三方文件才值得还原。
    """
    m = Manifest.load(game_dir)
    owned = {f["path"] for f in m.files}
    actions: list[str] = []

    for entry in m.files:
        p = game_dir / entry["path"]
        if p.is_file():
            p.unlink()
            actions.append(f"removed {entry['path']}")

    for b in m.backups:
        saved = game_dir / b["saved_to"]
        if saved.is_file() and b["original"] not in owned:
            shutil.copy2(saved, game_dir / b["original"])
            actions.append(f"restored {b['original']} from backup")

    shutil.rmtree(game_dir / MANIFEST_DIR, ignore_errors=True)
    actions.append(f"removed {MANIFEST_DIR}/")
    return actions
