"""安装编排：preflight → 扫描 → 选代理 → 备份/清理旧件 → 落盘 → 验证，失败回滚。"""
import json
import shutil
from dataclasses import dataclass, field
from pathlib import Path

from . import __version__
from .fetch import verify_kit
from .gpu import SUPPORTED, detect_gpu, driver_meets_minimum
from .ini import build_ini
from .manifest import MANIFEST_DIR, Manifest
from .proxy_select import PROXY_CANDIDATES, choose_proxy
from .scan import scan_game_dir

INI_NAME = "dlssg_sm86.ini"


@dataclass
class InstallResult:
    ok: bool
    proxy_name: str | None = None
    actions: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    guidance: list[str] = field(default_factory=list)


def _fail(warnings: list[str]) -> InstallResult:
    return InstallResult(ok=False, warnings=warnings)


def _kit_commit(kit_dir: Path) -> str:
    meta = kit_dir / "kit.json"
    if not meta.is_file():
        return "unknown"
    return json.loads(meta.read_text(encoding="utf-8")).get("dlssg_commit", "unknown")


def install(
    game_dir: Path,
    kit_dir: Path,
    *,
    tier: int = 1,
    mfg: str = "4x",
    runtime: str = "310.9",
    arch: str | None = None,
    allow_dxgi: bool = False,
) -> InstallResult:
    """把 dlssg_for_sm86 插帧层装进游戏目录；绝不触碰第三方 DLL。"""
    if not game_dir.is_dir():
        return _fail([f"game directory not found: {game_dir}"])

    # 1. preflight：显卡架构
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

    # 2. kit 校验（缺文件/哈希不符 → 拒绝安装）
    problems = verify_kit(kit_dir, runtime=runtime)
    if problems:
        return _fail([f"kit not healthy: {p}" for p in problems])
    kit_root = kit_dir / "dlssg" / runtime

    # 3. 读取旧 manifest → 扫描 → 选代理
    old_manifest: Manifest | None = None
    try:
        old_manifest = Manifest.load(game_dir)
    except FileNotFoundError:
        pass
    our_files = Manifest.our_file_names(old_manifest) if old_manifest else set()
    scan = scan_game_dir(game_dir, our_files=our_files | {INI_NAME})
    foreign = {n for n, kind in scan.existing_proxies.items() if kind == "foreign"}
    choice = choose_proxy(foreign, allow_dxgi=allow_dxgi)
    if choice is None:
        return _fail(
            ["所有代理名均被第三方占用: " + ", ".join(sorted(foreign))
             + "；请清理后重试（本工具绝不覆盖第三方 DLL）"]
        )

    # 4. 备份并移除我们自己的旧文件（重装/升级路径）
    #    不变量：只允许删代理候选名与 ini——manifest 是可被外部编辑的数据，
    #    绝不据其触碰其他路径。
    backup_dir = game_dir / MANIFEST_DIR / "backups"
    deletable = set(PROXY_CANDIDATES) | {INI_NAME}
    new_manifest = Manifest(
        dlss_combo_version=__version__,
        dlssg={
            "commit": _kit_commit(kit_dir),
            "runtime": runtime,
            "proxy_name": choice.name,
            "tier": tier,
            "mfg": mfg,
        },
    )
    created: list[Path] = []
    deleted: list[tuple[Path, Path]] = []  # (原路径, 备份路径)
    try:
        if old_manifest is not None:
            for entry in old_manifest.files:
                if entry["path"] not in deletable:
                    warnings.append(
                        f"manifest 中列出的非代理路径已跳过、未触碰: {entry['path']}"
                    )
                    continue
                p = game_dir / entry["path"]
                if p.is_file():
                    backup_dir.mkdir(parents=True, exist_ok=True)
                    saved = backup_dir / f"{entry['path']}.bak"
                    shutil.copy2(p, saved)
                    deleted.append((p, saved))
                    new_manifest.record_backup(
                        entry["path"], str(saved.relative_to(game_dir))
                    )
                p.unlink(missing_ok=True)

        # 5. 写入 ini 与所选代理
        ini_text = build_ini(tier=tier, mfg=mfg)
        ini_path = game_dir / INI_NAME
        ini_path.write_text(ini_text, encoding="utf-8", newline="\n")
        created.append(ini_path)
        src = kit_root / "version.dll" if choice.source == "root" else kit_root / "alternatives" / choice.name
        dst = game_dir / choice.name
        shutil.copy2(src, dst)
        created.append(dst)
        new_manifest.record_file(INI_NAME, new_manifest.sha256_of(ini_path), origin="kit")
        new_manifest.record_file(choice.name, new_manifest.sha256_of(dst), origin="kit")
        new_manifest.save(game_dir)
    except Exception:
        for p in created:
            p.unlink(missing_ok=True)
        for original, backup in deleted:
            if not original.exists():
                shutil.copy2(backup, original)
        raise

    # 6. 验证 + 画质层状态 + 指引
    actions = [
        f"已安装代理: {choice.name} (来源 {choice.source}, runtime {runtime}, commit {new_manifest.dlssg['commit']})",
        f"已写入 {INI_NAME} (tier={tier}, mfg={mfg})",
    ]
    guidance = []
    if scan.reshade or scan.renodx or scan.feeder:
        guidance.append(
            "已检测到 DLSS 5 画质层（ReShade/Feeder/RenoDX），与插帧层共存，无需额外配置"
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
        "日志与排障: game_dir/dlssg_sm86/logs/（doctor 子命令可代查）",
        "重启游戏后生效；卸载用 dlss-combo uninstall",
    ])
    return InstallResult(
        ok=True,
        proxy_name=choice.name,
        actions=actions,
        warnings=warnings,
        guidance=guidance,
    )
