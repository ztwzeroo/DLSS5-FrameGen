"""kit 缓存下载器：安装时才从上游官方渠道拉取二进制并做 SHA256 校验。"""
import hashlib
import json
import urllib.request
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Callable

DLSSG_REPO = "sdli1995/dlssg_for_sm86"
RAW_BASE = f"https://raw.githubusercontent.com/{DLSSG_REPO}"
COMMIT_API = f"https://api.github.com/repos/{DLSSG_REPO}/commits/main"
ALT_NAMES = ["winmm", "d3d12", "dbghelp", "dinput8", "dxgi"]
KIT_JSON = "kit.json"


@dataclass
class KitInfo:
    root: Path                 # kit_dir/dlssg/<runtime>
    dlssg_commit: str
    sha256: dict[str, str]     # kit 相对路径 -> sha256


def kit_files(runtime: str) -> dict[str, str]:
    """返回 {仓库路径: kit 相对路径}；310.9 在仓库根，310.1 在 310.1/ 前缀下。"""
    if runtime not in ("310.9", "310.1"):
        raise ValueError(f"unknown runtime {runtime!r}")
    base = "" if runtime == "310.9" else "310.1/"
    mapping = {
        f"{base}version.dll": f"dlssg/{runtime}/version.dll",
        "dlssg_sm86.ini": f"dlssg/{runtime}/dlssg_sm86.ini",
    }
    for n in ALT_NAMES:
        mapping[f"{base}alternatives/{n}.dll"] = f"dlssg/{runtime}/alternatives/{n}.dll"
    return mapping


def _default_fetch(url: str) -> bytes:
    req = urllib.request.Request(url, headers={"User-Agent": "dlss-combo/0.1"})
    with urllib.request.urlopen(req, timeout=120) as resp:
        return resp.read()


def _resolve_commit(fetch_bytes: Callable[[str], bytes]) -> str:
    raw = fetch_bytes(COMMIT_API)
    sha = json.loads(raw.decode("utf-8")).get("sha")
    if not sha:
        raise RuntimeError(f"cannot resolve {DLSSG_REPO}@main commit")
    return sha


def _load_meta(kit_dir: Path) -> dict:
    p = kit_dir / KIT_JSON
    if not p.is_file():
        return {}
    return json.loads(p.read_text(encoding="utf-8"))


def fetch_kit(
    kit_dir: Path,
    runtime: str = "310.9",
    refresh: bool = False,
    fetch_bytes: Callable[[str], bytes] | None = None,
) -> KitInfo:
    """下载/补齐 kit；已有完整 kit 且未 refresh 时直接返回。网络异常原样抛出。"""
    fetch_bytes = fetch_bytes or _default_fetch
    mapping = kit_files(runtime)
    meta = _load_meta(kit_dir)
    files_meta: dict[str, str] = dict(meta.get("files", {}))

    if not refresh and all(
        (kit_dir / kit_rel).is_file() for kit_rel in mapping.values()
    ):
        return KitInfo(
            root=kit_dir / "dlssg" / runtime,
            dlssg_commit=meta.get("dlssg_commit", "unknown"),
            sha256=files_meta,
        )

    commit = _resolve_commit(fetch_bytes)
    for repo_path, kit_rel in mapping.items():
        target = kit_dir / kit_rel
        target.parent.mkdir(parents=True, exist_ok=True)
        data = fetch_bytes(f"{RAW_BASE}/{commit}/{repo_path}")
        target.write_bytes(data)
        files_meta[kit_rel] = hashlib.sha256(data).hexdigest()

    meta = {
        "version": 1,
        "dlssg_commit": commit,
        "fetched_at": datetime.now(timezone.utc).isoformat(),
        "files": files_meta,
    }
    (kit_dir / KIT_JSON).write_text(
        json.dumps(meta, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    return KitInfo(root=kit_dir / "dlssg" / runtime, dlssg_commit=commit, sha256=files_meta)


def verify_kit(kit_dir: Path, runtime: str = "310.9") -> list[str]:
    """校验 kit：必需文件齐全且哈希与 kit.json 一致；返回问题清单（空 = 健康）。"""
    from .manifest import Manifest

    meta = _load_meta(kit_dir)
    if not meta:
        return [f"{KIT_JSON} missing at {kit_dir}"]
    problems: list[str] = []
    recorded: dict[str, str] = meta.get("files", {})
    for kit_rel in kit_files(runtime).values():
        p = kit_dir / kit_rel
        if not p.is_file():
            problems.append(f"missing: {kit_rel}")
        elif kit_rel in recorded and Manifest.sha256_of(p) != recorded[kit_rel]:
            problems.append(f"hash mismatch: {kit_rel}")
    return problems
