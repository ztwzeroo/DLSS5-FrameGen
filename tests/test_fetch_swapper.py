import json
from pathlib import Path

import pytest

from dlss_combo.fetch import fetch_swapper

API_LATEST = "https://api.github.com/repos/rakanki911/DLSS5-Swapper/releases/latest"


def _net(*, portable_name: str = "DLSS5Swapper-2.2.7-portable.zip"):
    zip_bytes = b"PK-swapper-portable"
    sums = (
        f"{__import__('hashlib').sha256(zip_bytes).hexdigest()}  {portable_name}\n"
        "deadbeef  other-asset.exe\n"
    ).encode()
    api = json.dumps(
        {
            "tag_name": "v2.2.7",
            "assets": [
                {"name": "DLSS5Swapper-2.2.7-setup.exe", "browser_download_url": "https://x/setup.exe"},
                {"name": portable_name, "browser_download_url": f"https://x/{portable_name}"},
                {"name": "SHA256SUMS.txt", "browser_download_url": "https://x/SHA256SUMS.txt"},
            ],
        }
    ).encode()

    def fetch_bytes(url: str) -> bytes:
        if url == API_LATEST:
            return api
        if url.endswith(portable_name):
            return zip_bytes
        if url.endswith("SHA256SUMS.txt"):
            return sums
        raise RuntimeError(f"unexpected {url}")

    return fetch_bytes


def test_fetch_swapper_downloads_and_verifies(tmp_path: Path):
    info = fetch_swapper(tmp_path, fetch_bytes=_net())
    z = tmp_path / "swapper" / "DLSS5Swapper-2.2.7-portable.zip"
    assert z.read_bytes() == b"PK-swapper-portable"
    assert info.tag == "v2.2.7" and info.zip_path == z


def test_fetch_swapper_records_in_kit_json(tmp_path: Path):
    fetch_swapper(tmp_path, fetch_bytes=_net())
    meta = json.loads((tmp_path / "kit.json").read_text())
    assert meta["swapper"]["tag"] == "v2.2.7"


def test_fetch_swapper_detects_checksum_mismatch(tmp_path: Path):
    def bad_sums(url: str) -> bytes:
        if url.endswith("SHA256SUMS.txt"):
            return b"0000000000000000000000000000000000000000000000000000000000000000  DLSS5Swapper-2.2.7-portable.zip\n"
        return _net()(url)

    with pytest.raises(RuntimeError, match="checksum"):
        fetch_swapper(tmp_path, fetch_bytes=bad_sums)


def test_fetch_swapper_skips_when_cached(tmp_path: Path):
    calls: list[str] = []

    def counting(url: str) -> bytes:
        calls.append(url)
        return _net()(url)

    fetch_swapper(tmp_path, fetch_bytes=counting)
    fetch_swapper(tmp_path, fetch_bytes=counting)
    assert len(calls) == 3  # api+zip+sums 只发生一次


def test_fetch_swapper_accepts_portable_exe(tmp_path: Path):
    """现实场景：上游 portable 资产是 .exe，且无 SHA256SUMS 资产。"""
    zip_bytes = b"PK-swapper-portable"

    def net(url: str) -> bytes:
        if url == API_LATEST:
            return json.dumps(
                {
                    "tag_name": "v2.2.7",
                    "assets": [
                        {"name": "DLSS5-Swapper-2.2.7-portable.exe", "browser_download_url": "https://x/p.exe"},
                        {"name": "DLSS5-Swapper-Setup-2.2.7.exe", "browser_download_url": "https://x/s.exe"},
                    ],
                }
            ).encode()
        if url == "https://x/p.exe":
            return zip_bytes
        raise RuntimeError(f"unexpected {url}")

    info = fetch_swapper(tmp_path, fetch_bytes=net)
    assert info.zip_path.name == "DLSS5-Swapper-2.2.7-portable.exe"
    assert info.zip_path.read_bytes() == zip_bytes
    meta = json.loads((tmp_path / "kit.json").read_text())
    assert meta["swapper"]["checksum_source"] == "self"
    assert len(meta["swapper"]["sha256"]) == 64


def test_fetch_swapper_no_portable_asset_raises(tmp_path: Path):
    def no_zip(url: str) -> bytes:
        if url == API_LATEST:
            return json.dumps(
                {"tag_name": "v1", "assets": [{"name": "setup.exe", "browser_download_url": "https://x/s.exe"}]}
            ).encode()
        raise RuntimeError("should not download anything")

    with pytest.raises(RuntimeError, match="portable"):
        fetch_swapper(tmp_path, fetch_bytes=no_zip)
