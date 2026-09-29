"""W5(b): lock the proxy fallback order cited from upstream alternatives docs."""
from dlss_combo.proxy_select import DXGI, PROXY_CANDIDATES, choose_proxy


def test_candidate_order_tools_first_render_path_last():
    assert PROXY_CANDIDATES == [
        "version.dll", "winmm.dll", "dbghelp.dll", "dinput8.dll", "d3d12.dll", "dxgi.dll",
    ]
    assert PROXY_CANDIDATES.index("d3d12.dll") == len(PROXY_CANDIDATES) - 2
    assert PROXY_CANDIDATES[-1] == DXGI


def test_choose_proxy_picks_first_free_name():
    assert choose_proxy({"version.dll"}).name == "winmm.dll"
    assert choose_proxy({"version.dll", "winmm.dll", "dbghelp.dll", "dinput8.dll", "d3d12.dll"}) is None
    assert choose_proxy({"version.dll", "winmm.dll", "dbghelp.dll", "dinput8.dll", "d3d12.dll"}, allow_dxgi=True).name == DXGI
