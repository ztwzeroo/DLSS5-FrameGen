"""Daily upstream-structure smoke for CI (W1). Read-only; never posts anywhere.

Green = upstream shape still matches what dlss-combo expects (commit resolves,
kit files exist, ini keys intact, swapper portable asset selectable).
NOTE: dlssg publishes no checksums — our kit hashes are self-computed for local
integrity; this check watches STRUCTURE, not upstream authenticity.
Usage: python scripts/upstream_check.py [--selftest]
"""
from __future__ import annotations

import json
import sys
import urllib.request
from pathlib import Path
from typing import Callable

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from dlss_combo.fetch import DLSSG_REPO, kit_files, select_portable_asset  # noqa: E402
from dlss_combo.ini import build_ini, missing_ini_keys  # noqa: E402

COMMIT_API = f"https://api.github.com/repos/{DLSSG_REPO}/commits/main"
RAW = f"https://raw.githubusercontent.com/{DLSSG_REPO}"
SWAPPER_API = "https://api.github.com/repos/rakanki911/DLSS5-Swapper/releases/latest"


def run_checks(fetch_bytes: Callable[[str], bytes]) -> list[str]:
    problems: list[str] = []

    def guarded(url: str) -> bytes | None:
        # 任何取回失败都转成检查项（含 GitHub 匿名限流），绝不让脚本带 traceback 崩掉
        try:
            return fetch_bytes(url)
        except Exception as e:  # noqa: BLE001 — 把一切取回失败都转成检查项
            problems.append(f"{url}: {type(e).__name__}: {e}")
            return None

    def guarded_json(url: str) -> dict | None:
        blob = guarded(url)
        if blob is None:
            return None
        try:
            parsed = json.loads(blob)
        except ValueError as e:
            problems.append(f"{url}: non-JSON body: {type(e).__name__}: {e}")
            return None
        if not isinstance(parsed, dict):
            problems.append(f"{url}: unexpected JSON body type: {type(parsed).__name__}")
            return None
        return parsed

    commit = guarded_json(COMMIT_API)
    if commit is None:
        return problems
    sha = commit.get("sha")
    if not isinstance(sha, str) or not sha:
        return [f"{COMMIT_API}: no sha in response"]
    for runtime in ("310.9", "310.1"):
        for repo_path in kit_files(runtime):
            url = f"{RAW}/{sha}/{repo_path}"
            blob = guarded(url)
            if blob is not None and not blob:
                problems.append(f"{url}: empty body")
    ini_blob = guarded(f"{RAW}/{sha}/dlssg_sm86.ini")
    if ini_blob is not None:
        ini_text = ini_blob.decode("utf-8", errors="replace")
        problems.extend(f"upstream dlssg_sm86.ini missing key: {m}" for m in missing_ini_keys(ini_text))
    release = guarded_json(SWAPPER_API)
    if release is not None:
        assets = {a["name"]: a.get("browser_download_url", "") for a in release.get("assets", [])}
        if select_portable_asset(assets) is None:
            problems.append(f"{SWAPPER_API}: no portable asset among {sorted(assets)}")
    return problems


def _default_fetch(url: str) -> bytes:
    req = urllib.request.Request(url, headers={"User-Agent": "dlss-combo/0.2"})
    with urllib.request.urlopen(req, timeout=60) as resp:
        return resp.read()


def _selftest() -> int:
    """Offline judgment matrix: run run_checks against synthetic upstreams."""
    sha = "b" * 40
    ini = build_ini()
    from dlss_combo.fetch import kit_files

    def make(*, drop_kit=False, rename_key=False, no_portable=False, no_sha=False):
        table = {
            COMMIT_API: json.dumps({"sha": "" if no_sha else sha}).encode(),
            f"{RAW}/{sha}/dlssg_sm86.ini": ini.replace("Optimized=", "Renamed=").encode()
            if rename_key else ini.encode(),
            SWAPPER_API: json.dumps({"assets": [
                {"name": "Setup.exe" if no_portable else "X-portable.exe",
                 "browser_download_url": "https://x"}
            ]}).encode(),
        }
        for runtime in ("310.9", "310.1"):
            for p in kit_files(runtime):
                # 根 dlssg_sm86.ini 同 URL 双重身份：真实 ini 文本优先，kit 二进制只补缺
                table.setdefault(
                    f"{RAW}/{sha}/{p}",
                    b"" if (drop_kit and p.endswith("version.dll")) else b"MZ",
                )
        return table

    cases = [
        ("healthy", make(), set(), 0),
        # 两个 kit 故障场景必须真实不同：缺失 = 取回该 URL 直接抛异常；空 = 取回成功但 body 为空
        ("missing kit file (fetch raises)", make(), {f"{RAW}/{sha}/version.dll"}, 1),
        ("empty kit body", make(drop_kit=True), set(), 1),
        ("ini key drift", make(rename_key=True), set(), 1),
        ("no portable asset", make(no_portable=True), set(), 1),
        ("no sha", make(no_sha=True), set(), 1),
    ]
    failed = 0
    for name, table, dead_urls, expected_problems in cases:
        def fetch(url: str, _table=table, _dead=dead_urls) -> bytes:
            if url in _dead:
                raise OSError(f"connection refused: {url}")
            return _table[url]

        problems = run_checks(fetch)
        ok = (len(problems) >= 1) == (expected_problems >= 1)
        print(f"{'PASS' if ok else 'FAIL'} selftest[{name}]: {problems}")
        failed += 0 if ok else 1
    return 1 if failed else 0


def main(argv: list[str] | None = None) -> int:
    args = sys.argv[1:] if argv is None else argv
    if "--selftest" in args:
        return _selftest()
    problems = run_checks(_default_fetch)
    for p in problems:
        print(f"FAIL {p}")
    if not problems:
        print("upstream structure OK: dlssg main HEAD, kit files, ini keys, swapper portable asset")
    return 1 if problems else 0


if __name__ == "__main__":
    raise SystemExit(main())
