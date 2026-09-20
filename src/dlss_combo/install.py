"""安装编排：preflight → 扫描 → 归属判定 → 选代理 → 原子落盘 → 验证，失败回滚。

不变量（对应审查 B/C/E）：
- 破坏性操作前先比对哈希：被外部修改的文件一律视为第三方，保留不动
- 首次安装覆盖用户 INI 前备份为 pre-existing，卸载时还原
- 所有落盘走临时文件 + os.replace；回滚清理临时件并从备份还原已删件
"""
import json
import os
import shutil
import tempfile
from dataclasses import dataclass, field
from pathlib import Path

from . import __version__
from .fetch import verify_kit
from .gpu import SUPPORTED, detect_gpu, driver_meets_minimum
from .ini import MFG_PRESET, build_ini
from .manifest import INI_NAME, MANIFEST_DIR, Manifest
from .proxy_select import choose_proxy
from .scan import scan_game_dir


@dataclass
class InstallResult:
    ok: bool
    proxy_name: str | None = None
    actions: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    guidance: list[str] = field(default_factory=list)


def _fail(warnings: list[str]) -> InstallResult:
    return InstallResult(ok=False, warnings=warnings)


def _kit_commit(kit_dir: Path, runtime: str) -> str:
    meta = kit_dir / "kit.json"
    if not meta.is_file():
        return "unknown"
    data = json.loads(meta.read_text(encoding="utf-8"))
    commits = data.get("dlssg_commits", {})
    return commits.get(runtime) or data.get("dlssg_commit", "unknown")


def _staged_temp(target: Path) -> Path:
    """同目录随机排他创建的临时文件（mkstemp=O_CREAT|O_EXCL，符号链接无法预占）。"""
    fd, name = tempfile.mkstemp(prefix=".dlsscombo-", suffix=".tmp", dir=str(target.parent))
    os.close(fd)
    return Path(name)


def _atomic_copy(src: Path, dst: Path, temps: set[Path]) -> None:
    tmp = _staged_temp(dst)
    temps.add(tmp)
    shutil.copy2(src, tmp)
    os.replace(tmp, dst)
    temps.discard(tmp)


def _atomic_write_text(dst: Path, text: str, temps: set[Path]) -> None:
    tmp = _staged_temp(dst)
    temps.add(tmp)
    tmp.write_text(text, encoding="utf-8", newline="\n")
    os.replace(tmp, dst)
    temps.discard(tmp)


def install(
    game_dir: Path,
    kit_dir: Path,
    *,
    tier: int = 1,
    mfg: str = "4x",
    runtime: str = "310.9",
    arch: str | None = None,
    allow_dxgi: bool = False,
    proxy: str | None = None,
) -> InstallResult:
    """把 dlssg_for_sm86 插帧层装进游戏目录；绝不触碰第三方文件。"""
    if not game_dir.is_dir():
        return _fail([f"game directory not found: {game_dir}"])

    # 1. preflight：显卡架构 + 驱动 + 能力组合
    if runtime == "310.1" and MFG_PRESET.get(mfg) == 5:
        return _fail(["310.1 运行库最高支持 4X（上游 INI 明示），6X 仅 310.9 可用；请改用 --mfg 4x 或 --runtime 310.9"])
    gpu = detect_gpu(override=arch)
    if gpu.arch is not None and gpu.arch not in SUPPORTED:
        return _fail(
            [f"unsupported GPU arch {gpu.arch} (detected: {gpu.name or gpu.source}); "
             f"dlssg_for_sm86 targets RTX 20 (sm75) / RTX 30 (sm86)"]
        )
    warnings: list[str] = []
    if gpu.arch is None:
        warnings.append("无法确认 GPU 架构（无 nvidia-smi？）——已继续，请自行确认是 RTX 20/30")
    if driver_meets_minimum(gpu.driver_version) is False:
        warnings.append(
            f"驱动 {gpu.driver_version} 低于 R580：DLSS-G 内核将走 PTX JIT 回退"
            "（首帧慢）甚至不可用，建议升级 NVIDIA 驱动"
        )

    # 2. kit 校验（缺文件/缺哈希/哈希不符 → 拒绝安装）
    problems = verify_kit(kit_dir, runtime=runtime)
    if problems:
        return _fail([f"kit not healthy: {p}" for p in problems])
    kit_root = kit_dir / "dlssg" / runtime

    # 3. 读取并验证旧 manifest → 哈希归属判定
    old_manifest: Manifest | None = None
    try:
        old_manifest = Manifest.load(game_dir)
    except FileNotFoundError:
        pass
    except (json.JSONDecodeError, KeyError, TypeError) as e:
        return _fail([f"manifest 损坏，拒绝安装（可手动删除 .dlss-combo 后重试）: {e}"])
    if old_manifest is not None:
        try:
            old_manifest.validate(game_dir)
        except ValueError as e:
            return _fail([f"manifest 校验失败，拒绝安装: {e}"])

    externally_modified: set[str] = set()
    truly_ours: list[dict] = []
    if old_manifest is not None:
        for entry in old_manifest.files:
            match = old_manifest.current_hash_matches(game_dir, entry["path"])
            if match is True:
                truly_ours.append(entry)
            elif match is False:
                externally_modified.add(entry["path"])

    scan = scan_game_dir(
        game_dir, our_files={e["path"] for e in truly_ours} | {INI_NAME}
    )
    foreign = {n for n, kind in scan.existing_proxies.items() if kind == "foreign"}
    occupied = foreign | externally_modified
    choice = choose_proxy(occupied, allow_dxgi=allow_dxgi, force=proxy)
    if choice is None:
        return _fail(
            ["代理名不可用（被第三方或外部修改文件占用）: " + ", ".join(sorted(occupied))
             + "；请换 --proxy 或清理后重试（本工具绝不覆盖第三方 DLL）"]
        )

    # 4. 备份与清理：只动"哈希仍一致的本工具文件"；外部修改的保留并警告
    backup_dir = game_dir / MANIFEST_DIR / "backups"
    new_manifest = Manifest(
        dlss_combo_version=__version__,
        dlssg={
            "commit": _kit_commit(kit_dir, runtime),
            "runtime": runtime,
            "proxy_name": choice.name,
            "tier": tier,
            "mfg": mfg,
        },
    )
    if old_manifest is not None:
        # 跨升级继承最早的 pre-existing 备份记录（用户原文件只记第一次）
        for b in old_manifest.backups:
            if b.get("kind", "pre-existing") == "pre-existing":
                new_manifest.backups.append(dict(b))

    created: list[Path] = []
    deleted: list[tuple[Path, Path]] = []  # (原路径, 备份路径)
    overwrote: list[tuple[Path, Path]] = []  # 本次覆盖的预存文件 (目标, 安装前备份)
    temps: set[Path] = set()  # 仅本操作登记的临时文件
    try:
        for entry in truly_ours:
            p = game_dir / entry["path"]
            if p.is_file():
                backup_dir.mkdir(parents=True, exist_ok=True)
                saved = backup_dir / f"{entry['path']}.bak"
                shutil.copy2(p, saved)
                deleted.append((p, saved))
                new_manifest.record_backup(
                    entry["path"], str(saved.relative_to(game_dir)), kind="ours-history"
                )
            p.unlink(missing_ok=True)
        for name in sorted(externally_modified):
            warnings.append(
                f"文件已被外部修改、按第三方保留（如需本工具管理请先自行处理）: {name}"
            )

        # 首次安装：用户已有的 INI 先备份为 pre-existing（卸载时还原）
        # 备份名与 ours-history（*.bak）分开，避免重装时覆盖用户原件；
        # 覆盖行为纳入回滚事务：后续任一步失败都从这份备份还原用户原件
        ini_path = game_dir / INI_NAME
        pre_backup: Path | None = None
        if ini_path.is_file() and not any(
            b.get("original") == INI_NAME
            and b.get("kind", "pre-existing") == "pre-existing"
            for b in new_manifest.backups
        ):
            already_ours = any(e["path"] == INI_NAME for e in truly_ours)
            if not already_ours:
                backup_dir.mkdir(parents=True, exist_ok=True)
                saved = backup_dir / f"{INI_NAME}.pre.bak"
                shutil.copy2(ini_path, saved)
                pre_backup = saved
                new_manifest.record_backup(
                    INI_NAME,
                    str(saved.relative_to(game_dir)),
                    kind="pre-existing",
                    sha256=new_manifest.sha256_of(saved),
                )
        if pre_backup is not None:
            overwrote.append((ini_path, pre_backup))

        # 5. 原子落盘
        # INI 被外部修改（或曾被外部修改并标记）→ 保留用户版本，不再写入
        ini_user_managed = INI_NAME in externally_modified or bool(
            old_manifest and old_manifest.dlssg.get("ini_user_managed")
        )
        if ini_user_managed and ini_path.is_file():
            warnings.append(
                "dlssg_sm86.ini 已被外部修改：保留你的版本，本次 tier/mfg 未写入"
                "（删除该文件后重装可恢复本工具管理）"
            )
            new_manifest.dlssg["ini_user_managed"] = True
        else:
            _atomic_write_text(ini_path, build_ini(tier=tier, mfg=mfg), temps)
            created.append(ini_path)
            new_manifest.record_file(
                INI_NAME, new_manifest.sha256_of(ini_path), origin="kit"
            )
        src = (
            kit_root / "version.dll"
            if choice.source == "root"
            else kit_root / "alternatives" / choice.name
        )
        dst = game_dir / choice.name
        _atomic_copy(src, dst, temps)
        created.append(dst)
        new_manifest.record_file(choice.name, new_manifest.sha256_of(dst), origin="kit")
        new_manifest.save(game_dir)
    except Exception:
        for p in created:
            p.unlink(missing_ok=True)
        for t in temps:  # 只清理本操作登记的临时文件（R3：绝不碰无关同名后缀）
            t.unlink(missing_ok=True)
        for original, backup in deleted:
            if not original.exists() or original.read_bytes() != backup.read_bytes():
                shutil.copy2(backup, original)
        for target, backup in overwrote:  # R1：首次覆盖的用户原件从预存备份还原
            shutil.copy2(backup, target)
        raise
    for t in temps:
        t.unlink(missing_ok=True)

    # 6. 验证 + 画质层状态 + 指引
    actions = [
        f"已安装代理: {choice.name} (来源 {choice.source}, runtime {runtime}, commit {new_manifest.dlssg['commit']})",
    ]
    if new_manifest.dlssg.get("ini_user_managed"):
        actions.append("保留用户修改的 dlssg_sm86.ini（未写入本工具配置）")
    else:
        actions.append(f"已写入 {INI_NAME} (tier={tier}, mfg={mfg})")
    guidance = []
    if scan.reshade or scan.renodx or scan.feeder:
        guidance.append(
            "已检测到 ReShade/Feeder/RenoDX 痕迹（DLSS 5 画质层的载体）——"
            "痕迹不等于组件齐全，请进游戏确认画质层已生效"
        )
    else:
        guidance.append(
            "未检测到 DLSS 5 画质层：先用 DLSS5-Swapper 给本游戏安装 DLSS 5 神经渲染，再回来享受组合效果"
        )
    if scan.optiscaler:
        warnings.append("检测到 OptiScaler：它与插帧层都钩 NGX 链路，如遇异常请只保留其一")
    tamper = new_manifest.verify(game_dir)
    if tamper:
        warnings.extend(tamper)

    guidance.extend([
        "进游戏设置开启 DLSS 帧生成（2X/3X/4X）；基础帧率 ≥55–60 再开 4X，6X 要求更高",
        "验证生效: 日志 dlssg_sm86/logs/loader_*.jsonl 出现 runtime_redirect，或跑 doctor",
        "重启游戏后生效；卸载用 dlss-combo uninstall",
    ])
    return InstallResult(
        ok=True,
        proxy_name=choice.name,
        actions=actions,
        warnings=warnings,
        guidance=guidance,
    )
