import json
from pathlib import Path

import pytest

from dlss_combo.fetch import fetch_kit, verify_kit

FILES_3109 = {
    "commits/main": b'{"sha": "abc1234"}',
    "version.dll": b"dll3109",
    "dlssg_sm86.ini": b"[General]",
    "alternatives/winmm.dll": b"w",
    "alternatives/d3d12.dll": b"d3",
    "alternatives/dbghelp.dll": b"db",
    "alternatives/dinput8.dll": b"di",
    "alternatives/dxgi.dll": b"dx",
}


def make_fetch(files: dict[str, bytes]):
    def fetch_bytes(url: str) -> bytes:
        for key, blob in files.items():
            if url.endswith(key):
                return blob
        raise RuntimeError(f"unexpected url {url}")

    return fetch_bytes


def test_fetch_writes_kit_and_json(tmp_path: Path):
    kit = fetch_kit(tmp_path, fetch_bytes=make_fetch(FILES_3109))
    assert (kit.root / "version.dll").read_bytes() == b"dll3109"
    assert kit.dlssg_commit == "abc1234"
    meta = json.loads((tmp_path / "kit.json").read_text())
    assert meta["dlssg_commit"] == "abc1234"
    assert len(meta["files"]) == 7


def test_verify_kit_healthy_after_fetch(tmp_path: Path):
    fetch_kit(tmp_path, fetch_bytes=make_fetch(FILES_3109))
    assert verify_kit(tmp_path) == []


def test_verify_kit_detects_tampering(tmp_path: Path):
    kit = fetch_kit(tmp_path, fetch_bytes=make_fetch(FILES_3109))
    (kit.root / "version.dll").write_bytes(b"tampered")
    problems = verify_kit(tmp_path)
    assert any("version.dll" in p for p in problems)


def test_verify_kit_detects_missing_files(tmp_path: Path):
    kit = fetch_kit(tmp_path, fetch_bytes=make_fetch(FILES_3109))
    (kit.root / "alternatives" / "dxgi.dll").unlink()
    problems = verify_kit(tmp_path)
    assert any("dxgi.dll" in p for p in problems)


def test_fetch_is_idempotent_without_refresh(tmp_path: Path):
    calls = []

    def tracking_fetch(url: str) -> bytes:
        calls.append(url)
        return make_fetch(FILES_3109)(url)

    fetch_kit(tmp_path, fetch_bytes=tracking_fetch)
    n_first = len(calls)
    kit = fetch_kit(tmp_path, fetch_bytes=tracking_fetch)
    assert len(calls) == n_first  # 第二次未重复下载
    assert kit.dlssg_commit == "abc1234"


def test_fetch_3101_uses_prefixed_repo_paths(tmp_path: Path):
    files = dict(FILES_3109)
    files["310.1/version.dll"] = b"dll3101"
    files["310.1/alternatives/winmm.dll"] = b"w1"
    files["310.1/alternatives/d3d12.dll"] = b"d31"
    files["310.1/alternatives/dbghelp.dll"] = b"db1"
    files["310.1/alternatives/dinput8.dll"] = b"di1"
    files["310.1/alternatives/dxgi.dll"] = b"dx1"
    kit = fetch_kit(tmp_path, runtime="310.1", fetch_bytes=make_fetch(files))
    assert (tmp_path / "dlssg" / "310.1" / "version.dll").read_bytes() == b"dll3101"


def test_fetch_no_network_raises(tmp_path: Path):
    def net_down(url: str) -> bytes:
        raise RuntimeError("net down")

    with pytest.raises(RuntimeError):
        fetch_kit(tmp_path, fetch_bytes=net_down)
