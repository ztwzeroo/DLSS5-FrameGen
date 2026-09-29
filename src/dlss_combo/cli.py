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
        description="DLSS 5 image upscaling (DLSS5-Swapper) + DLSS frame generation "
                    "(dlssg_for_sm86) combo installer",
    )
    p.add_argument("--version", action="version", version=f"dlss-combo {__version__}")
    p.add_argument("--check-update", action="store_true",
                   help="check GitHub for a newer dlss-combo release, then continue")
    sub = p.add_subparsers(dest="command", required=False)

    pf = sub.add_parser("fetch", help="download/update the kit cache (upstream binaries)")
    pf.add_argument("--kit-dir", type=Path, default=DEFAULT_KIT)
    pf.add_argument("--runtime", choices=["310.9", "310.1"], default="310.9")
    pf.add_argument("--refresh", action="store_true", help="force re-download")

    pi = sub.add_parser("install", help="install the frame-gen layer into a game directory")
    pi.add_argument("game_dir", type=Path)
    pi.add_argument("--kit-dir", type=Path, default=DEFAULT_KIT)
    pi.add_argument("--mfg", choices=sorted(MFG_PRESET), default="4x")
    pi.add_argument("--tier", type=int, choices=[0, 1, 2, 3], default=1)
    pi.add_argument("--runtime", choices=["310.9", "310.1"], default="310.9")
    pi.add_argument("--arch", help="explicit GPU arch sm75/sm86 (when detection fails or to override)")
    pi.add_argument("--allow-dxgi", action="store_true",
                    help="allow the dxgi.dll proxy name (commonly used by ReShade/OptiScaler; think twice)")
    pi.add_argument("--proxy", choices=[
        "version.dll", "winmm.dll", "dbghelp.dll", "dinput8.dll", "d3d12.dll", "dxgi.dll",
    ], help="explicit proxy DLL name (default: first free slot in upstream-recommended order)")
    pi.add_argument("--launch-swapper", action="store_true",
                    help="launch the kit's DLSS5-Swapper portable after install (image layer)")

    pu = sub.add_parser("uninstall", help="restore the pre-install state from the manifest")
    pu.add_argument("game_dir", type=Path)

    pd = sub.add_parser("doctor", help="read-only health check: routing logs, conflicts, image layer")
    pd.add_argument("game_dir", type=Path)

    pr = sub.add_parser("report", help="print a paste-ready markdown report for the game-test issue")
    pr.add_argument("game_dir", type=Path)
    pr.add_argument("--out", type=Path, help="also write the report to this file")
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
    if getattr(args, "check_update", False):
        from .update import check_update

        info = check_update(__version__)
        if info.status == "available":
            print(f"update available: {info.latest_tag} -> {info.url}")
        elif info.status == "latest":
            print(f"dlss-combo {__version__} is up to date (latest: {info.latest_tag})")
        else:
            print("update check skipped (network unavailable)")
    try:
        if args.command == "fetch":
            from .fetch import fetch_kit, fetch_swapper

            kit = fetch_kit(args.kit_dir, runtime=args.runtime, refresh=args.refresh)
            print(f"dlssg kit ready: {kit.root} (commit {kit.dlssg_commit})")
            try:
                sw = fetch_swapper(args.kit_dir, refresh=args.refresh)
                print(f"DLSS5-Swapper portable ready: {sw.zip_path} ({sw.tag})")
            except Exception as e:
                print(f"[warn] DLSS5-Swapper download failed (you can grab it manually from "
                      f"its GitHub releases page): {e}", file=sys.stderr)
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
                print(f"[ok] {line}")
            for line in result.warnings:
                print(f"[warn] {line}")
            for line in result.guidance:
                print(f"[info] {line}")
            if result.ok and args.launch_swapper:
                try:
                    exe = launch_swapper(args.kit_dir)
                    print(f"[ok] launched DLSS5-Swapper: {exe.name}")
                    print("[info] once the Swapper has DLSS 5 installed for this game, "
                          "run doctor again to re-check")
                except FileNotFoundError as e:
                    print(f"[warn] {e}", file=sys.stderr)
            return 0 if result.ok else 1

        if args.command == "uninstall":
            from .uninstall import uninstall

            for line in uninstall(args.game_dir):
                print(f"[ok] {line}")
            return 0

        if args.command == "doctor":
            from .doctor import doctor

            if not args.game_dir.is_dir():
                print(f"error: directory not found: {args.game_dir}", file=sys.stderr)
                return 2
            report = doctor(args.game_dir)
            for line in report.lines:
                print(line)
            return 1 if report.has_problems else 0

        if args.command == "report":
            from .report import ISSUE_URL, build_report

            text = build_report(args.game_dir)
            print(text)
            print(f"\nPaste this into the game-test issue: {ISSUE_URL}")
            if args.out:
                args.out.write_text(text + "\n", encoding="utf-8")
                print(f"report written to {args.out}")
            return 0

    except FileNotFoundError as e:
        print(f"error: {e}", file=sys.stderr)
        return 2
    except ValueError as e:
        print(f"error: {e}", file=sys.stderr)
        return 2
    except Exception as e:  # 网络/IO 等意外，给出可读信息而非栈
        print(f"error: {type(e).__name__}: {e}", file=sys.stderr)
        return 3
    if args.command is None:  # 裸调用（无子命令）：仅 --check-update 可返回 0
        return 0 if getattr(args, "check_update", False) else 2
    return 0
