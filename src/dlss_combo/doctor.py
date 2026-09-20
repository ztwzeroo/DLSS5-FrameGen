"""诊断：解析 dlssg 日志确认插帧路由生效，报告冲突与画质层状态。

准确性规则（审查 G）：同一日志取最后一条 route 事件、跨日志取最新；
active 必须是严格布尔；检测到坏哈希或 route=false 计为问题（CLI 返回非零）。
"""
import json
from dataclasses import dataclass, field
from pathlib import Path

from .manifest import Manifest
from .scan import scan_game_dir


@dataclass
class DoctorReport:
    lines: list[str] = field(default_factory=list)
    route_active: bool | None = None
    problems: list[str] = field(default_factory=list)

    @property
    def has_problems(self) -> bool:
        return bool(self.problems)


def _parse_route_active(text: str) -> bool | None:
    """同一条日志里取最后一条 route 事件的 active（严格布尔）；没有则 None。"""
    result: bool | None = None
    for line in text.splitlines():
        line = line.strip()
        if not line or "route" not in line:
            continue
        try:
            obj = json.loads(line)
        except json.JSONDecodeError:
            continue
        if not isinstance(obj, dict):
            continue
        route = obj.get("route")
        if isinstance(route, dict):
            active = route.get("active")
            if active is True or active is False:
                result = active  # 持续覆盖 → 最后一条生效
    return result


def doctor(game_dir: Path) -> DoctorReport:
    """对游戏目录做只读体检，输出人读的诊断行。"""
    if not game_dir.is_dir():
        rep = DoctorReport(lines=[f"目录不存在: {game_dir}"])
        rep.problems.append("game dir missing")
        return rep

    try:
        manifest = Manifest.load(game_dir)
        ours = Manifest.our_file_names(manifest)
    except FileNotFoundError:
        ours = set()
        manifest = None
    except (json.JSONDecodeError, KeyError, TypeError):
        rep = DoctorReport(lines=["manifest 损坏，无法诊断"])
        rep.problems.append("manifest corrupt")
        return rep

    scan = scan_game_dir(game_dir, our_files=ours)
    rep = DoctorReport()
    log_dir = game_dir / "dlssg_sm86" / "logs"

    # 1. 插帧路由是否生效：诊断范围=最新一份日志；更早日志只作历史参考（R6）
    source_log: Path | None = None
    historical: list[tuple[str, bool]] = []
    if log_dir.is_dir():
        logs = sorted(log_dir.glob("backend_*.jsonl"), key=lambda p: p.stat().st_mtime, reverse=True)
        for idx, log in enumerate(logs):
            result = _parse_route_active(log.read_text(encoding="utf-8", errors="replace"))
            if idx == 0:
                if result is not None:
                    rep.route_active = result
                    source_log = log
            elif result is not None:
                historical.append((log.name, result))
    if rep.route_active is True:
        rep.lines.append(f"OK: dlssg 插帧路由已生效（最新日志 {source_log.name if source_log else ''} route active=true）")
    elif rep.route_active is False:
        rep.lines.append(
            "问题: 最新 backend 日志显示 route active=false——驱动/运行库未匹配，"
            "把 ini 的 [Logging] Level 提到 2 后重开游戏复现"
        )
        rep.problems.append("route active=false")
    else:
        rep.lines.append(
            "未验证：最新日志没有 route 事件（本次会话未确认生效）；"
            "日志在 dlssg_sm86/logs/，先跑一局游戏再查"
        )
    for name, active in historical:
        rep.lines.append(
            f"历史参考: 更早的 {name} 曾报告 route active={'true' if active else 'false'}"
            "（不代表本次会话）"
        )

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

    # 3. 画质层（痕迹 ≠ 组件齐全/已生效，如实表述）
    if scan.reshade or scan.renodx or scan.feeder:
        rep.lines.append("已检测到 ReShade/Feeder/RenoDX 痕迹（DLSS 5 画质层载体）；痕迹不代表画质层已在游戏内生效，请进游戏确认")
    else:
        rep.lines.append("提示: 可用 DLSS5-Swapper 加装 DLSS 5 画质层，与插帧层组合获得更好画面")

    if scan.optiscaler:
        rep.lines.append("注意: 检测到 OptiScaler——与插帧层重复钩 NGX，异常时二选一")

    # 4. manifest 完整性
    if manifest is not None:
        try:
            manifest.validate(game_dir)
        except ValueError as e:
            rep.lines.append(f"问题: manifest 校验失败: {e}")
            rep.problems.append("manifest invalid")
        else:
            problems = manifest.verify(game_dir)
            if problems:
                rep.lines.extend(f"问题: {p}" for p in problems)
                rep.problems.extend(problems)
            else:
                rep.lines.append("OK: manifest 校验通过，文件未被篡改")
    else:
        rep.lines.append("提示: 无 dlss-combo manifest——插帧层可能不是本工具装的")

    return rep
