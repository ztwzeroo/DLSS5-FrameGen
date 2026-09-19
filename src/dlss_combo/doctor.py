"""诊断：解析 dlssg 日志确认插帧路由生效，报告冲突与画质层状态。"""
import json
from dataclasses import dataclass, field
from pathlib import Path

from .scan import scan_game_dir


@dataclass
class DoctorReport:
    lines: list[str] = field(default_factory=list)
    route_active: bool | None = None


def _parse_route_active(text: str) -> bool | None:
    """在 JSONL 文本中找 route 的 active 字段；找不到返回 None。"""
    for line in text.splitlines():
        line = line.strip()
        if not line or "route" not in line:
            continue
        try:
            obj = json.loads(line)
        except json.JSONDecodeError:
            continue
        route = obj.get("route")
        if isinstance(route, dict) and "active" in route:
            return bool(route["active"])
    return None


def doctor(game_dir: Path) -> DoctorReport:
    """对游戏目录做只读体检，输出人读的诊断行。"""
    if not game_dir.is_dir():
        return DoctorReport(lines=[f"目录不存在: {game_dir}"], route_active=None)

    from .manifest import Manifest

    try:
        manifest = Manifest.load(game_dir)
        ours = Manifest.our_file_names(manifest)
    except FileNotFoundError:
        ours = set()
        manifest = None

    scan = scan_game_dir(game_dir, our_files=ours)
    rep = DoctorReport()
    log_dir = game_dir / "dlssg_sm86" / "logs"

    # 1. 插帧路由是否生效（backend 日志）
    if log_dir.is_dir():
        for log in sorted(log_dir.glob("backend_*.jsonl")):
            result = _parse_route_active(log.read_text(encoding="utf-8", errors="replace"))
            if result is not None:
                rep.route_active = result
    if rep.route_active is True:
        rep.lines.append("OK: dlssg 插帧路由已生效（backend 日志 route active=true）")
    elif rep.route_active is False:
        rep.lines.append("问题: backend 日志显示 route active=false——驱动/运行库未匹配，"
                         "把 ini 的 [Logging] Level 提到 2 后重开游戏复现")
    else:
        rep.lines.append("未找到 route 记录：日志在 dlssg_sm86/logs/（先跑一局游戏生成 backend_*.jsonl）")

    # 2. 代理冲突
    proxies = sorted(scan.existing_proxies)
    if len(proxies) > 1:
        rep.lines.append(
            f"注意: 多个代理 DLL 并存 {proxies}——按上游说明首个被游戏加载者生效、"
            "其余仅转发；ReShade/画质层的 dxgi.dll 与插帧代理并存属预期，异常时再精简"
        )
    foreign = [n for n, k in scan.existing_proxies.items() if k == "foreign"]
    if manifest is None and foreign:
        rep.lines.append(f"注意: {foreign} 非本工具安装（无 manifest）——如有异常先排查这些 DLL")

    # 3. 画质层
    if scan.reshade or scan.renodx or scan.feeder:
        rep.lines.append("OK: 检测到 DLSS 5 画质层（ReShade/Feeder/RenoDX）")
    else:
        rep.lines.append("提示: 可用 DLSS5-Swapper 加装 DLSS 5 画质层，与插帧层组合获得更好画面")

    if scan.optiscaler:
        rep.lines.append("注意: 检测到 OptiScaler——与插帧层重复钩 NGX，异常时二选一")

    # 4. manifest 完整性
    if manifest is not None:
        problems = manifest.verify(game_dir)
        rep.lines.extend(problems or ["OK: manifest 校验通过，文件未被篡改"])
    else:
        rep.lines.append("提示: 无 dlss-combo manifest——插帧层可能不是本工具装的")

    return rep
