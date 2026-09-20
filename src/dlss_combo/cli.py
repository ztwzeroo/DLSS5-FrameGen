"""命令行入口：fetch / install / uninstall / doctor。"""
import argparse
import sys
from pathlib import Path

from . import __version__
from .ini import MFG_PRESET

DEFAULT_KIT = Path.home() / "dlss-combo-kit"


def _build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        prog="dlss-combo",
        description="DLSS 5 画质（DLSS5-Swapper）+ DLSS 帧生成（dlssg_for_sm86）组合安装器",
    )
    p.add_argument("--version", action="version", version=f"dlss-combo {__version__}")
    sub = p.add_subparsers(dest="command", required=True)

    pf = sub.add_parser("fetch", help="下载/更新 kit 缓存（上游二进制）")
    pf.add_argument("--kit-dir", type=Path, default=DEFAULT_KIT)
    pf.add_argument("--runtime", choices=["310.9", "310.1"], default="310.9")
    pf.add_argument("--refresh", action="store_true", help="强制重新下载")

    pi = sub.add_parser("install", help="把插帧层装进游戏目录")
    pi.add_argument("game_dir", type=Path)
    pi.add_argument("--kit-dir", type=Path, default=DEFAULT_KIT)
    pi.add_argument("--mfg", choices=sorted(MFG_PRESET), default="4x")
    pi.add_argument("--tier", type=int, choices=[0, 1, 2, 3], default=1)
    pi.add_argument("--runtime", choices=["310.9", "310.1"], default="310.9")
    pi.add_argument("--arch", help="显式指定架构 sm75/sm86（探测失败或需覆盖时用）")
    pi.add_argument("--allow-dxgi", action="store_true",
                    help="允许占用 dxgi.dll 代理名（ReShade/OptiScaler 常用，慎选）")
    pi.add_argument("--proxy", choices=[
        "version.dll", "winmm.dll", "dbghelp.dll", "dinput8.dll", "d3d12.dll", "dxgi.dll",
    ], help="显式指定代理 DLL 名（默认按上游推荐顺序取空闲位）")
    pi.add_argument("--launch-swapper", action="store_true",
                    help="安装后自动拉起 kit 中的 DLSS5-Swapper portable（画质层）")

    pu = sub.add_parser("uninstall", help="按 manifest 还原安装前状态")
    pu.add_argument("game_dir", type=Path)

    pd = sub.add_parser("doctor", help="只读体检：路由日志、冲突、画质层")
    pd.add_argument("game_dir", type=Path)
    return p


def main(argv: list[str] | None = None) -> int:
    # 冻结为 exe 后 Windows 控制台默认代码页不是 UTF-8，中文输出会炸
    for stream in (sys.stdout, sys.stderr):
        try:
            stream.reconfigure(encoding="utf-8", errors="replace")
        except (AttributeError, OSError):
            pass
    try:
        args = _build_parser().parse_args(argv)
    except SystemExit as e:  # argparse 参数错误 → 退出码而非异常
        return e.code if isinstance(e.code, int) else 2
    try:
        if args.command == "fetch":
            from .fetch import fetch_kit, fetch_swapper

            kit = fetch_kit(args.kit_dir, runtime=args.runtime, refresh=args.refresh)
            print(f"dlssg kit 就绪: {kit.root} (commit {kit.dlssg_commit})")
            try:
                sw = fetch_swapper(args.kit_dir, refresh=args.refresh)
                print(f"DLSS5-Swapper portable 就绪: {sw.zip_path} ({sw.tag})")
            except Exception as e:
                print(f"[警告] DLSS5-Swapper 下载失败（可用图形界面手动下载）: {e}",
                      file=sys.stderr)
            return 0

        if args.command == "install":
            from .fetch import launch_swapper
            from .install import install

            result = install(
                args.game_dir,
                args.kit_dir,
                tier=args.tier,
                mfg=args.mfg,
                runtime=args.runtime,
                arch=args.arch,
                allow_dxgi=args.allow_dxgi,
                proxy=args.proxy,
            )
            for line in result.actions:
                print(f"[动作] {line}")
            for line in result.warnings:
                print(f"[警告] {line}")
            for line in result.guidance:
                print(f"[指引] {line}")
            if result.ok and args.launch_swapper:
                try:
                    exe = launch_swapper(args.kit_dir)
                    print(f"[动作] 已拉起 DLSS5-Swapper: {exe.name}")
                    print("[指引] 在 Swapper 里给本游戏装好 DLSS 5 后，回来跑 doctor 复检")
                except FileNotFoundError as e:
                    print(f"[警告] {e}", file=sys.stderr)
            return 0 if result.ok else 1

        if args.command == "uninstall":
            from .uninstall import uninstall

            for line in uninstall(args.game_dir):
                print(f"[动作] {line}")
            return 0

        if args.command == "doctor":
            from .doctor import doctor

            if not args.game_dir.is_dir():
                print(f"错误: 目录不存在: {args.game_dir}", file=sys.stderr)
                return 2
            report = doctor(args.game_dir)
            for line in report.lines:
                print(line)
            return 1 if report.has_problems else 0

    except FileNotFoundError as e:
        print(f"错误: {e}", file=sys.stderr)
        return 2
    except ValueError as e:
        print(f"错误: {e}", file=sys.stderr)
        return 2
    except Exception as e:  # 网络/IO 等意外，给出可读信息而非栈
        print(f"错误: {type(e).__name__}: {e}", file=sys.stderr)
        return 3
    return 0
