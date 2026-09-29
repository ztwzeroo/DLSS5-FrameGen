"""Multi-source download fallback: official sources first, community mirrors last,
every failure surfaces what was tried. We never redistribute upstream files — we
only fetch them from upstream's own channels (mirrors proxy those channels)."""
import pytest

from dlss_combo.fetch import DEFAULT_MIRRORS, alternate_urls, fetch_with_fallback

RAW = "https://raw.githubusercontent.com/sdli1995/dlssg_for_sm86/abc123def/version.dll"
ASSET = (
    "https://github.com/rakanki911/DLSS5-Swapper/releases/download/v2.2.8/"
    "DLSS5Swapper-2.2.8-portable.exe"
)


def test_alternate_urls_for_raw_file_github_raw_then_mirrors():
    alts = alternate_urls(RAW)
    assert alts[0] == "https://github.com/sdli1995/dlssg_for_sm86/raw/abc123def/version.dll"
    for mirror in DEFAULT_MIRRORS:
        assert any(a.startswith(mirror) for a in alts), mirror
    # official alternate comes before every mirror
    for a in alts[1:]:
        assert a.startswith(tuple(DEFAULT_MIRRORS)), a


def test_alternate_urls_for_release_asset_mirror_prefixes_original():
    alts = alternate_urls(ASSET)
    assert any(a.endswith(ASSET) for a in alts)
    assert not any("/raw/" in a for a in alts)


def test_alternate_urls_passthrough_for_unknown_hosts():
    assert alternate_urls("https://example.com/x.bin") == []


def test_fetch_with_fallback_primary_first_when_reachable():
    calls: list[str] = []

    def opener(url: str) -> bytes:
        calls.append(url)
        return b"DATA"

    assert fetch_with_fallback(RAW, opener) == b"DATA"
    assert calls == [RAW]


def test_fetch_with_fallback_falls_through_to_first_working_source():
    attempts: list[str] = []

    def opener(url: str) -> bytes:
        attempts.append(url)
        # 只按域名前缀拦截官方源；镜像 URL 虽含原始 URL 后缀，但域名不同、应放行
        if url.startswith("https://github.com/") or url.startswith(
            "https://raw.githubusercontent.com/"
        ):
            raise OSError("blocked")
        return b"MIRROR-DATA"

    assert fetch_with_fallback(RAW, opener) == b"MIRROR-DATA"
    assert attempts[0] == RAW
    assert len(attempts) >= 2 and attempts[1] != RAW


def test_fetch_with_fallback_all_sources_fail_lists_everything():
    def opener(url: str) -> bytes:
        raise OSError("down")

    with pytest.raises(RuntimeError) as ei:
        fetch_with_fallback(RAW, opener)
    msg = str(ei.value)
    assert RAW in msg
    assert "alternate" in msg


def test_mirror_list_overridable_via_env(monkeypatch):
    monkeypatch.setenv("DLSS_COMBO_MIRRORS", "https://m1.example/,https://m2.example/")
    alts = alternate_urls(RAW)
    assert any(a.startswith("https://m1.example/") for a in alts)
    assert any(a.startswith("https://m2.example/") for a in alts)
    assert not any(a.startswith(tuple(DEFAULT_MIRRORS)) for a in alts)
