"""Assemble a paste-ready markdown report for the game-test issue template.
Read-only, fully offline; never uploads, never opens a browser.
"""
from __future__ import annotations

import platform
from pathlib import Path
from typing import Callable

from . import __version__
from .doctor import doctor
from .manifest import Manifest

ISSUE_URL = "https://github.com/ztwzeroo/DLSS5-FrameGen/issues/new?template=game-test.yml"


def _manifest_lines(game_dir: Path) -> list[str]:
    try:
        m = Manifest.load(game_dir)
    except FileNotFoundError:
        return ["- install manifest: **not installed by dlss-combo**"]
    except Exception:  # noqa: BLE001 — 报告只陈述，不判定
        return ["- install manifest: present but unreadable"]
    d = m.dlssg if isinstance(m.dlssg, dict) else {}
    return [
        f"- install manifest: present (schema v{m.version}, tool v{m.dlss_combo_version})",
        f"- frame-gen layer: runtime {d.get('runtime', '?')}, proxy `{d.get('proxy_name', '?')}`, "
        f"mfg {d.get('mfg', '?')}, tier {d.get('tier', '?')}, "
        f"upstream commit `{str(d.get('commit', '?'))[:12]}`",
        f"- tracked files: {len(m.files)}",
    ]


def _gpu_lines(gpu_runner: Callable[[str], str] | None) -> list[str]:
    # Worktree isolation: import lazily (multi-GPU lands with Task 2 at merge time)
    try:
        from .gpu import choose_gpu, detect_all_gpus
        gpus = detect_all_gpus(gpu_runner)
    except ImportError:
        return ["- GPU: detection unavailable in this build"]
    if not gpus:
        return ["- GPU: not detected (nvidia-smi unavailable)"]
    primary = choose_gpu(gpus)
    out = []
    for g in gpus:
        mark = " *(selected)*" if g is primary else ""
        out.append(f"- GPU: {g.name} — arch {g.arch}, driver {g.driver_version}{mark}")
    return out


def build_report(game_dir: Path, gpu_runner: Callable[[str], str] | None = None) -> str:
    rep = doctor(game_dir)
    verdict = ("frame-gen route ACTIVE" if rep.route_active is True
               else "frame-gen route INACTIVE" if rep.route_active is False
               else "frame-gen route UNVERIFIED")
    image_files = getattr(rep, "image_layer_files", [])
    lines = [
        "## dlss-combo game-test report",
        f"- dlss-combo version: {__version__} on {platform.platform()}",
        *_manifest_lines(game_dir),
        *_gpu_lines(gpu_runner),
        f"- doctor verdict: {verdict}",
        (f"- image layer: files present (not proof of an active layer): {image_files}"
         if image_files else "- image layer: no ReShade/RenoDX/Feeder files found"),
    ]
    if rep.problems:
        lines.append("- problems:")
        lines.extend(f"  - {p}" for p in rep.problems)
    else:
        lines.append("- problems: none reported by doctor")
    lines.append("- doctor output:")
    lines.extend(f"  > {ln}" for ln in rep.lines)
    lines.append("")
    lines.append("**What this report does NOT contain:** no FPS, image-quality or latency "
                 "measurements; in-game behavior of the combined setup is unverified by this tool.")
    return "\n".join(lines)
