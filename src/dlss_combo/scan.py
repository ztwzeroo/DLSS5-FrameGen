"""扫描游戏目录：代理占用、ReShade/RenoDX/Feeder/OptiScaler 检测。"""
from dataclasses import dataclass
from pathlib import Path

from .proxy_select import PROXY_CANDIDATES


@dataclass
class GameScan:
    path: Path
    existing_proxies: dict[str, str]  # 文件名 -> "ours" | "foreign"
    reshade: bool
    optiscaler: bool
    renodx: bool
    feeder: bool
    has_our_install: bool


def scan_game_dir(game_dir: Path, our_files: set[str] | None = None) -> GameScan:
    """枚举目录中与安装相关的现状；our_files 是 manifest 记录的本工具文件名集合。"""
    our_files = our_files or set()
    existing: dict[str, str] = {}
    for name in PROXY_CANDIDATES:
        if (game_dir / name).is_file():
            existing[name] = "ours" if name in our_files else "foreign"
    try:
        entries = list(game_dir.iterdir())
    except OSError:
        entries = []
    files = {e.name.lower() for e in entries if e.is_file()}
    dirs = {e.name.lower() for e in entries if e.is_dir()}
    # 空 reshade-shaders 文件夹不构成 ReShade 证据（审查 G：避免误报画质层）
    reshade_dir = game_dir / "reshade-shaders"
    shaders_nonempty = reshade_dir.is_dir() and any(reshade_dir.iterdir())
    reshade = shaders_nonempty or (
        ("dxgi.dll" in files) and ("reshade.ini" in files)
    )
    optiscaler = ("optiscaler.ini" in files) or ("optiscaler" in dirs)
    renodx = any(n.startswith("renodx") for n in files)
    feeder = any("feeder" in n for n in files)
    return GameScan(
        path=game_dir,
        existing_proxies=existing,
        reshade=reshade,
        optiscaler=optiscaler,
        renodx=renodx,
        feeder=feeder,
        has_our_install=any(v == "ours" for v in existing.values()),
    )
