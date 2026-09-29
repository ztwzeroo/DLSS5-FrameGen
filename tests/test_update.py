"""W4: update check is informational; all failures degrade to 'unknown'."""
import json

from dlss_combo.update import UpdateInfo, check_update, parse_tag


def _api(fetch, tag="v0.9.9", url="https://x/rel"):
    return lambda: fetch(json.dumps({"tag_name": tag, "html_url": url}).encode())


def test_parse_tag_strips_v_and_pads():
    assert parse_tag("v0.2.0") == (0, 2, 0)
    assert parse_tag("1.2") > parse_tag("1.1.9")
    assert parse_tag("junk") == (0,)


def test_newer_release_reported():
    info = check_update("0.1.3", fetch_bytes=lambda u: json.dumps(
        {"tag_name": "v0.2.0", "html_url": "https://x"}).encode())
    assert info == UpdateInfo("available", "v0.2.0", "https://x")


def test_same_or_older_is_latest():
    info = check_update("0.2.0", fetch_bytes=lambda u: json.dumps(
        {"tag_name": "v0.2.0", "html_url": "https://x"}).encode())
    assert info.status == "latest"


def test_network_failure_is_unknown_not_raise():
    def boom(u):
        raise OSError("offline")
    assert check_update("0.2.0", fetch_bytes=boom).status == "unknown"
    assert check_update("0.2.0", fetch_bytes=lambda u: b"not json").status == "unknown"
