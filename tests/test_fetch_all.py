"""`fetch --runtime all` downloads both runtimes plus the Swapper in one command."""
import json

from dlss_combo.cli import main
from dlss_combo.fetch import KitInfo, SwapperInfo


def test_cli_fetch_runtime_all_fetches_both_runtimes(tmp_path, monkeypatch, capsys):
    import dlss_combo.fetch as fetch_mod

    kit_calls: list[str] = []

    def fake_fetch_kit(kit_dir, runtime="310.9", refresh=False, fetch_bytes=None):
        kit_calls.append(runtime)
        return KitInfo(root=kit_dir / "dlssg" / runtime, dlssg_commit="c" * 40, sha256={})

    def fake_fetch_swapper(kit_dir, refresh=False, fetch_bytes=None):
        return SwapperInfo(tag="v2.2.8", zip_path=kit_dir / "swapper" / "p.exe")

    monkeypatch.setattr(fetch_mod, "fetch_kit", fake_fetch_kit)
    monkeypatch.setattr(fetch_mod, "fetch_swapper", fake_fetch_swapper)

    rc = main(["fetch", "--kit-dir", str(tmp_path), "--runtime", "all"])

    assert rc == 0
    assert kit_calls == ["310.9", "310.1"]
    out = capsys.readouterr().out
    assert "310.9" in out and "310.1" in out


def test_cli_fetch_runtime_single_stays_single(tmp_path, monkeypatch):
    import dlss_combo.fetch as fetch_mod

    kit_calls: list[str] = []

    def fake_fetch_kit(kit_dir, runtime="310.9", refresh=False, fetch_bytes=None):
        kit_calls.append(runtime)
        return KitInfo(root=kit_dir / "dlssg" / runtime, dlssg_commit="c" * 40, sha256={})

    monkeypatch.setattr(fetch_mod, "fetch_kit", fake_fetch_kit)
    monkeypatch.setattr(fetch_mod, "fetch_swapper",
                        lambda k, refresh=False, fetch_bytes=None: SwapperInfo("", k))

    rc = main(["fetch", "--kit-dir", str(tmp_path), "--runtime", "310.1"])
    assert rc == 0
    assert kit_calls == ["310.1"]
