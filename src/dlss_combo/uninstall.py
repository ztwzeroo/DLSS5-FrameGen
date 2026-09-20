"""卸载：验证 manifest 与备份 → 只删哈希仍一致的本工具文件 → 还原用户原文件 → 清理。

安全规则（对应独立复核 R2/R5）：
- 动手前先验证全部 pre-existing 备份存在（且哈希匹配则校验）——缺失即中止，不删任何东西
- 另存恢复副本用排他创建（O_CREAT|O_EXCL）且名称冲突时递增，绝不覆盖任何现有文件或链接
"""
import os
import shutil
from pathlib import Path

from .manifest import MANIFEST_DIR, Manifest


def _exclusive_restore_copy(game_dir: Path, original: str, saved: Path) -> str:
    """把安装前原配置排他另存为 <original>.pre-existing[.N]；绝不覆盖已存在路径。"""
    stem = f"{original}.pre-existing"
    for i in range(100):
        cand = game_dir / (stem if i == 0 else f"{stem}.{i}")
        try:
            fd = os.open(cand, os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o644)
        except FileExistsError:
            continue  # 已有文件/符号链接都不动，试下一个名字
        with os.fdopen(fd, "wb") as out, open(saved, "rb") as inp:
            shutil.copyfileobj(inp, out)
        return cand.name
    raise RuntimeError(f"无法为 {original} 找到空闲的恢复副本名（前 100 个都被占用）")


def uninstall(game_dir: Path) -> list[str]:
    """还原到安装前状态；manifest 缺失抛 FileNotFoundError，非法抛 ValueError，
    pre-existing 备份缺失/损坏抛 RuntimeError（此时不做任何删除）。"""
    m = Manifest.load(game_dir)
    m.validate(game_dir)
    actions: list[str] = []

    pre_existing = [
        b for b in m.backups if b.get("kind", "pre-existing") == "pre-existing"
    ]
    # R5：任何删除发生前，先确认必需备份都在（且哈希可核则核）
    missing: list[str] = []
    corrupted: list[str] = []
    for b in pre_existing:
        saved = game_dir / b["saved_to"]
        if not saved.is_file():
            missing.append(b["saved_to"])
        elif b.get("sha256") and Manifest.sha256_of(saved) != b["sha256"]:
            corrupted.append(b["saved_to"])
    if missing or corrupted:
        raise RuntimeError(
            "pre-existing 备份"
            + ("缺失: " + ", ".join(missing) if missing else "")
            + (" 损坏: " + ", ".join(corrupted) if corrupted else "")
            + " —— 为保可恢复，已中止卸载且未删除任何文件；"
            f"请先从备份目录 {MANIFEST_DIR}/backups/ 找回或自行处理后再试"
        )

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

    for b in pre_existing:
        saved = game_dir / b["saved_to"]
        target = game_dir / b["original"]
        if target.exists() and b["original"] not in deleted_by_us:
            # 目标是外部修改后的用户文件：不覆盖，原配置排他另存副本
            side = _exclusive_restore_copy(game_dir, b["original"], saved)
            actions.append(
                f"保留用户修改的 {b['original']}；安装前原配置另存为 {side}"
            )
        else:
            shutil.copy2(saved, target)
            actions.append(f"restored {b['original']} from pre-existing backup")

    shutil.rmtree(game_dir / MANIFEST_DIR, ignore_errors=True)
    actions.append(f"removed {MANIFEST_DIR}/")
    return actions
