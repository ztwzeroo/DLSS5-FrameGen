"""卸载：验证 manifest → 只删哈希仍一致的本工具文件 → 还原用户原文件 → 清理。"""
import shutil
from pathlib import Path

from .manifest import MANIFEST_DIR, Manifest


def uninstall(game_dir: Path) -> list[str]:
    """还原到安装前状态；manifest 缺失抛 FileNotFoundError，非法则抛 ValueError。

    安全规则（审查 A/B）：
    - 动手前先整体校验 manifest（路径范围、schema 版本、备份位置）
    - 当前哈希与安装时不一致的文件视为外部修改，保留不动
    - 只还原 kind=pre-existing 的备份（用户原文件）；本工具历史版本备份直接丢弃
    """
    m = Manifest.load(game_dir)
    m.validate(game_dir)
    actions: list[str] = []
    deleted_by_us: set[str] = set()

    for entry in m.files:
        p = game_dir / entry["path"]
        if not p.is_file():
            continue
        if m.sha256_of(p) != entry["sha256"]:
            actions.append(f"保留（已被外部修改）: {entry['path']}")
            continue
        p.unlink()
        deleted_by_us.add(entry["path"])
        actions.append(f"removed {entry['path']}")

    for b in m.backups:
        if b.get("kind", "pre-existing") != "pre-existing":
            continue
        saved = game_dir / b["saved_to"]
        if not saved.is_file():
            continue
        target = game_dir / b["original"]
        if target.exists() and b["original"] not in deleted_by_us:
            # 目标是外部修改后的用户文件：不覆盖，原配置另存副本
            side_copy = game_dir / f"{b['original']}.pre-existing"
            shutil.copy2(saved, side_copy)
            actions.append(
                f"保留用户修改的 {b['original']}；安装前原配置另存为 {side_copy.name}"
            )
        else:
            shutil.copy2(saved, target)
            actions.append(f"restored {b['original']} from pre-existing backup")

    shutil.rmtree(game_dir / MANIFEST_DIR, ignore_errors=True)
    actions.append(f"removed {MANIFEST_DIR}/")
    return actions
