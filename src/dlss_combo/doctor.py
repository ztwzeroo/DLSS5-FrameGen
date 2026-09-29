"""诊断：解析 dlssg 日志确认插帧路由生效，报告冲突与画质层状态。

准确性规则（审查 G）：同一日志取最后一条 route 事件、跨日志取最新；
active 必须是严格布尔；检测到坏哈希或 route=false 计为问题（CLI 返回非零）。
"""
import json
from dataclasses import dataclass, field
from pathlib import Path

from .gpu import choose_gpu, detect_all_gpus
from .manifest import Manifest
from .scan import GameScan, scan_game_dir


@dataclass
class DoctorReport:
    lines: list[str] = field(default_factory=list)
    route_active: bool | None = None
    problems: list[str] = field(default_factory=list)
    # Image-layer marker files seen in the game dir (e.g. "ReShade") — evidence
    # only, never proof of an active layer; consumed by downstream reporting.
    image_layer_files: list[str] = field(default_factory=list)

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


def _image_layer_names(game_dir: Path, scan: GameScan) -> list[str]:
    """Image-layer file evidence (weaker than scan's "component complete" verdict):
    scan flags plus direct marker files — a bare ReShade.ini still proves the file
    is present, which is all the evidence tier claims."""
    try:
        names = {e.name.lower() for e in game_dir.iterdir()}
    except OSError:
        names = set()
    layers: list[str] = []
    if scan.reshade or "reshade.ini" in names:
        layers.append("ReShade")
    if scan.renodx:
        layers.append("RenoDX")
    if scan.feeder:
        layers.append("Feeder")
    return layers


def doctor(game_dir: Path) -> DoctorReport:
    """对游戏目录做只读体检，输出人读的诊断行。"""
    if not game_dir.is_dir():
        rep = DoctorReport(lines=[f"directory not found: {game_dir}"])
        rep.problems.append("game dir missing")
        return rep

    try:
        manifest = Manifest.load(game_dir)
        ours = Manifest.our_file_names(manifest)
    except FileNotFoundError:
        ours = set()
        manifest = None
    except (json.JSONDecodeError, KeyError, TypeError):
        rep = DoctorReport(lines=["manifest corrupt; cannot diagnose"])
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
            # An unreadable log degrades the diagnosis to a problem; never crash (W5).
            try:
                text = log.read_text(encoding="utf-8", errors="replace")
            except OSError:
                rep.problems.append(f"log unreadable: {log.name}")
                continue
            result = _parse_route_active(text)
            if idx == 0:
                if result is not None:
                    rep.route_active = result
                    source_log = log
            elif result is not None:
                historical.append((log.name, result))
    if rep.route_active is True:
        rep.lines.append(f"OK: dlssg frame-gen routing is active (latest log "
                         f"{source_log.name if source_log else ''} route active=true)")
    elif rep.route_active is False:
        rep.lines.append(
            "problem: latest backend log shows route active=false — driver/runtime "
            "mismatch; raise [Logging] Level to 2 in the ini and restart the game to reproduce"
        )
        rep.problems.append("route active=false")
    else:
        rep.lines.append(
            "unverified: the latest log has no route event (not confirmed this session); "
            "logs live in dlssg_sm86/logs/ — play a round first, then check again"
        )
    for name, active in historical:
        rep.lines.append(
            f"historical: older {name} reported route active={'true' if active else 'false'} "
            "(not this session)"
        )

    # 0. GPU landscape（多 NVIDIA 卡时列出全部，明确主卡与 --arch 覆盖）
    gpus = detect_all_gpus()
    nvidia = [g for g in gpus if g.vendor == "nvidia"]
    if len(nvidia) > 1:
        primary = choose_gpu(gpus)
        names = ", ".join(g.name for g in nvidia)
        rep.lines.append(
            f"note: multiple NVIDIA GPUs detected ({names}); using {primary.name or primary.arch} "
            "— pass --arch to override"
        )

    # 2. 代理冲突
    proxies = sorted(scan.existing_proxies)
    if len(proxies) > 1:
        rep.lines.append(
            f"note: multiple proxy DLLs coexist {proxies} — per upstream, the first one "
            "the game loads wins and the rest only forward; ReShade/image-layer dxgi.dll "
            "next to the frame-gen proxy is expected, trim only if things misbehave"
        )
    foreign = [n for n, k in scan.existing_proxies.items() if k == "foreign"]
    if manifest is None and foreign:
        rep.lines.append(f"note: {foreign} not installed by this tool (no manifest) — "
                         "check these DLLs first if anything misbehaves")

    # 3. Image layer (files present are evidence, never proof of activation)
    rep.image_layer_files = _image_layer_names(game_dir, scan)
    if rep.image_layer_files:
        rep.lines.append(
            "note: image-layer files present (not proof of an active layer): "
            + ", ".join(rep.image_layer_files)
        )
    else:
        rep.lines.append("hint: add the DLSS 5 image layer with DLSS5-Swapper and combine it "
                         "with the frame-gen layer for a better picture")

    if scan.optiscaler:
        rep.lines.append("note: OptiScaler detected — it duplicates the frame-gen layer's "
                         "NGX hooks; keep only one if things misbehave")

    # 4. manifest 完整性
    if manifest is not None:
        try:
            manifest.validate(game_dir)
        except ValueError as e:
            rep.lines.append(f"problem: manifest validation failed: {e}")
            rep.problems.append("manifest invalid")
        else:
            problems = manifest.verify(game_dir)
            if problems:
                rep.lines.extend(f"problem: {p}" for p in problems)
                rep.problems.extend(problems)
            else:
                rep.lines.append("OK: manifest validated, files untampered")
    else:
        rep.lines.append("hint: no dlss-combo manifest — the frame-gen layer may not have "
                         "been installed by this tool")

    return rep
