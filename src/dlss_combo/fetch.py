"""kit 缓存下载器：安装时才从上游官方渠道拉取二进制并做 SHA256 校验。

事务性（审查 D/F）：下载到 *.part 再原子替换；缓存命中时重新校验哈希、
损坏自动重下；kit.json 按运行库分别记录 commit，重建不丢其他组件元数据。
"""
import hashlib
import json
import os
import re
import shutil
import tempfile
import urllib.request
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Callable

from .manifest import Manifest

DLSSG_REPO = "sdli1995/dlssg_for_sm86"
RAW_BASE = f"https://raw.githubusercontent.com/{DLSSG_REPO}"
COMMIT_API = f"https://api.github.com/repos/{DLSSG_REPO}/commits/main"
ALT_NAMES = ["winmm", "d3d12", "dbghelp", "dinput8", "dxgi"]
KIT_JSON = "kit.json"
_SHA256_RE = re.compile(r"^[0-9a-f]{64}$")


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


def _verify_recorded(kit_dir: Path, recorded: dict[str, str], runtime: str) -> list[str]:
    """必需文件必须都有格式正确且匹配的哈希（审查 D：缺失即问题）。"""
    problems: list[str] = []
    for kit_rel in kit_files(runtime).values():
        p = kit_dir / kit_rel
        expected = recorded.get(kit_rel)
        if expected is None:
            problems.append(f"missing checksum: {kit_rel}")
        elif not _SHA256_RE.match(expected):
            problems.append(f"invalid checksum format: {kit_rel}")
        elif not p.is_file():
            problems.append(f"missing: {kit_rel}")
        elif Manifest.sha256_of(p) != expected:
            problems.append(f"hash mismatch: {kit_rel}")
    return problems


def fetch_kit(
    kit_dir: Path,
    runtime: str = "310.9",
    refresh: bool = False,
    fetch_bytes: Callable[[str], bytes] | None = None,
) -> KitInfo:
    """下载/补齐 kit；缓存命中时先校验，损坏或缺失才重新下载。"""
    fetch_bytes = fetch_bytes or _default_fetch
    mapping = kit_files(runtime)
    meta = _load_meta(kit_dir)
    files_meta: dict[str, str] = dict(meta.get("files", {}))
    commits: dict[str, str] = dict(meta.get("dlssg_commits", {}))

    if not refresh and not _verify_recorded(kit_dir, files_meta, runtime):
        return KitInfo(
            root=kit_dir / "dlssg" / runtime,
            dlssg_commit=commits.get(runtime, meta.get("dlssg_commit", "unknown")),
            sha256=files_meta,
        )

    commit = _resolve_commit(fetch_bytes)
    # R7：先全部下载进独立 staging，校验齐全后原子切换——
    # 中断/失败时旧 kit 保持完好（离线回退能力不丢）
    staging = kit_dir / ".staging"
    if staging.exists():
        shutil.rmtree(staging)
    staging.mkdir(parents=True)
    staged: dict[str, str] = {}
    try:
        for repo_path, kit_rel in mapping.items():
            target = staging / kit_rel
            target.parent.mkdir(parents=True, exist_ok=True)
            data = fetch_bytes(f"{RAW_BASE}/{commit}/{repo_path}")
            target.write_bytes(data)
            staged[kit_rel] = hashlib.sha256(data).hexdigest()
        # 全部就位 → 逐文件原子切换（文件各自完整，元数据最后提交）
        for kit_rel in mapping.values():
            final = kit_dir / kit_rel
            final.parent.mkdir(parents=True, exist_ok=True)
            os.replace(staging / kit_rel, final)
            files_meta[kit_rel] = staged[kit_rel]
    finally:
        shutil.rmtree(staging, ignore_errors=True)

    # 从现有 meta 出发更新，保留 swapper 与其他运行库的记录（审查 F）
    meta.setdefault("version", 1)
    meta["dlssg_commits"] = {**commits, runtime: commit}
    meta["fetched_at"] = datetime.now(timezone.utc).isoformat()
    meta["files"] = files_meta
    fd, tmp_name = tempfile.mkstemp(prefix=".dlsscombo-", suffix=".tmp", dir=str(kit_dir))
    tmp = Path(tmp_name)
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as fh:
            fh.write(json.dumps(meta, ensure_ascii=False, indent=2))
        os.replace(tmp, kit_dir / KIT_JSON)
    except BaseException:
        tmp.unlink(missing_ok=True)
        raise
    return KitInfo(root=kit_dir / "dlssg" / runtime, dlssg_commit=commit, sha256=files_meta)


def verify_kit(kit_dir: Path, runtime: str = "310.9") -> list[str]:
    """校验 kit：必需文件齐全、哈希齐全且匹配；返回问题清单（空 = 健康）。"""
    meta = _load_meta(kit_dir)
    if not meta:
        return [f"{KIT_JSON} missing at {kit_dir}"]
    return _verify_recorded(kit_dir, meta.get("files", {}), runtime)


SWAPPER_REPO = "rakanki911/DLSS5-Swapper"
SWAPPER_API = f"https://api.github.com/repos/{SWAPPER_REPO}/releases/latest"


@dataclass
class SwapperInfo:
    tag: str
    zip_path: Path


def fetch_swapper(
    kit_dir: Path,
    refresh: bool = False,
    fetch_bytes: Callable[[str], bytes] | None = None,
) -> SwapperInfo:
    """下载 DLSS5-Swapper 最新 portable 包；有官方校验文件则强校验，否则自记哈希。"""
    fetch_bytes = fetch_bytes or _default_fetch
    swapper_dir = kit_dir / "swapper"
    meta = _load_meta(kit_dir)
    cached = meta.get("swapper", {})
    if not refresh and cached.get("zip"):
        z = kit_dir / cached["zip"]
        recorded = cached.get("sha256", "")
        if z.is_file() and _SHA256_RE.match(recorded) and Manifest.sha256_of(z) == recorded:
            return SwapperInfo(tag=cached.get("tag", ""), zip_path=z)

    release = json.loads(fetch_bytes(SWAPPER_API).decode("utf-8"))
    assets = {a["name"]: a["browser_download_url"] for a in release.get("assets", [])}
    # 上游实际发布 *.portable.exe（也有过 .zip 的可能）；Setup 安装器不是我们要的
    portable_name = next(
        (n for n in assets
         if "portable" in n.lower() and n.lower().endswith((".zip", ".exe"))),
        None,
    )
    if portable_name is None:
        raise RuntimeError(f"no portable asset in {SWAPPER_REPO} latest release")

    blob = fetch_bytes(assets[portable_name])
    actual_sha = hashlib.sha256(blob).hexdigest()
    sums_name = next((n for n in assets if "sha256" in n.lower()), None)
    checksum_source = "self"  # 上游不总提供校验文件；默认自记哈希（本地完整性基线）
    if sums_name is not None:
        expected: str | None = None
        for line in fetch_bytes(assets[sums_name]).decode("utf-8").splitlines():
            parts = line.split(None, 1)
            if len(parts) == 2 and parts[1].strip().lstrip("*") == portable_name:
                expected = parts[0].strip().lower()
                break
        if expected is None:
            raise RuntimeError(f"checksum file has no entry for {portable_name}")
        if actual_sha != expected:
            raise RuntimeError(f"checksum mismatch for {portable_name}: {actual_sha} != {expected}")
        checksum_source = "upstream"

    swapper_dir.mkdir(parents=True, exist_ok=True)
    zip_path = swapper_dir / portable_name
    fd, part_name = tempfile.mkstemp(prefix=".dlsscombo-", suffix=".part", dir=str(swapper_dir))
    part = Path(part_name)
    try:
        with os.fdopen(fd, "wb") as fh:
            fh.write(blob)
        os.replace(part, zip_path)
    except BaseException:
        part.unlink(missing_ok=True)
        raise

    swapper_meta = {
        "tag": release.get("tag_name", ""),
        "zip": str(zip_path.relative_to(kit_dir)),
        "sha256": actual_sha,
        "checksum_source": checksum_source,
    }
    meta.setdefault("version", 1)
    meta["swapper"] = swapper_meta
    fd, tmp_name = tempfile.mkstemp(prefix=".dlsscombo-", suffix=".tmp", dir=str(kit_dir))
    tmp = Path(tmp_name)
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as fh:
            fh.write(json.dumps(meta, ensure_ascii=False, indent=2))
        os.replace(tmp, kit_dir / KIT_JSON)
    except BaseException:
        tmp.unlink(missing_ok=True)
        raise
    return SwapperInfo(tag=release.get("tag_name", ""), zip_path=zip_path)


def launch_swapper(
    kit_dir: Path,
    spawn: Callable[[Path], None] | None = None,
) -> Path:
    """校验后拉起 kit 里的 DLSS5-Swapper portable；zip 拒绝、哈希不符拒绝。"""
    meta = _load_meta(kit_dir)
    entry = meta.get("swapper", {})
    rel = entry.get("zip")
    if not rel:
        raise FileNotFoundError("kit 中没有 DLSS5-Swapper（先运行 dlss-combo fetch）")
    rel_path = Path(str(rel))
    if rel_path.is_absolute() or ".." in rel_path.parts:
        raise ValueError(f"Swapper 路径越界: {rel!r}")
    exe = kit_dir / rel_path
    if not exe.is_file():
        raise FileNotFoundError(f"DLSS5-Swapper 不在 kit 中: {exe}")
    if exe.suffix.lower() == ".zip":
        raise RuntimeError(
            "kit 中的 Swapper 是 zip 包：请解压后运行其中的 exe，或重新 fetch 获取 portable.exe"
        )
    recorded = str(entry.get("sha256", ""))
    if not _SHA256_RE.match(recorded) or Manifest.sha256_of(exe) != recorded:
        raise RuntimeError(f"hash mismatch: DLSS5-Swapper 哈希不符，拒绝启动: {exe.name}")
    (spawn or _default_spawn)(exe)
    return exe


def _default_spawn(exe: Path) -> None:
    import os
    import platform

    if platform.system() == "Windows":
        os.startfile(str(exe))  # noqa: S606 - Windows 惯例拉起 GUI
    else:
        import subprocess

        subprocess.Popen([str(exe)], start_new_session=True)
