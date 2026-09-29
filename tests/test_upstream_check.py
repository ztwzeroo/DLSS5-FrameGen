"""W1: upstream structure smoke — judgment matrix driven by fake network."""
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))

import upstream_check as uc  # noqa: E402
from dlss_combo.ini import build_ini, missing_ini_keys  # noqa: E402

SHA = "a" * 40


def healthy(updates=None):
    base = {
        uc.COMMIT_API: json.dumps({"sha": SHA}).encode(),
        f"{uc.RAW}/{SHA}/dlssg_sm86.ini": build_ini().encode(),
        f"{uc.RAW}/{SHA}/310.1/dlssg_sm86.ini": build_ini().encode(),
        uc.SWAPPER_API: json.dumps({"assets": [
            {"name": "DLSS5Swapper-2.2.7-portable.exe", "browser_download_url": "https://x/p.exe"},
        ]}).encode(),
    }
    from dlss_combo.fetch import kit_files
    for runtime in ("310.9", "310.1"):
        prefix = "" if runtime == "310.9" else "310.1/"
        for p in kit_files(runtime):
            # 根 dlssg_sm86.ini 既是 kit 文件也是被解析的 ini（同一 URL）：保留上面的真实 ini 文本
            base.setdefault(f"{uc.RAW}/{SHA}/{p}", b"MZ\x90\x00")
    if updates:
        base.update(updates)
    return base


def test_healthy_upstream_passes():
    assert uc.run_checks(lambda url: healthy()[url]) == []


def test_missing_kit_file_fails():
    bad = healthy()
    bad.pop(f"{uc.RAW}/{SHA}/version.dll")
    problems = uc.run_checks(lambda url: (_ for _ in ()).throw(LookupError(url)) if url not in bad else bad[url])
    assert any("version.dll" in p for p in problems)


def test_ini_key_drift_fails():
    drifted = build_ini().replace("Optimized=", "Renamed=")
    bad = healthy({f"{uc.RAW}/{SHA}/dlssg_sm86.ini": drifted.encode()})
    assert uc.run_checks(lambda url: bad[url])
    assert missing_ini_keys(drifted) == ["FrameGeneration.Optimized"]


def test_no_portable_asset_fails():
    bad = healthy({uc.SWAPPER_API: json.dumps({"assets": [
        {"name": "DLSS5Swapper-Setup-2.2.7.exe", "browser_download_url": "https://x/s.exe"},
    ]}).encode()})
    problems = uc.run_checks(lambda url: bad[url])
    assert any("portable" in p for p in problems)


def test_selftest_runs_green():
    assert uc.main(["--selftest"]) == 0
