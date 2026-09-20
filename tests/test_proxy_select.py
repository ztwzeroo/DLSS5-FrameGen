from dlss_combo.proxy_select import PROXY_CANDIDATES, ProxyChoice, choose_proxy


def test_empty_dir_gets_version_dll():
    assert choose_proxy(set()) == ProxyChoice(name="version.dll", source="root")


def test_occupied_version_falls_to_winmm():
    assert choose_proxy({"version.dll"}) == ProxyChoice(
        name="winmm.dll", source="alternatives"
    )


def test_dxgi_never_chosen_by_default():
    occ = {"version.dll", "winmm.dll", "d3d12.dll", "dbghelp.dll", "dinput8.dll"}
    assert choose_proxy(occ) is None


def test_dxgi_allowed_with_flag():
    occ = {"version.dll", "winmm.dll", "d3d12.dll", "dbghelp.dll", "dinput8.dll"}
    assert choose_proxy(occ, allow_dxgi=True) == ProxyChoice(
        name="dxgi.dll", source="alternatives"
    )


def test_all_occupied_returns_none():
    assert choose_proxy(set(PROXY_CANDIDATES), allow_dxgi=True) is None


def test_order_follows_candidates():
    assert [c.name for c in
            (choose_proxy({"version.dll", "winmm.dll"}),)] == ["dbghelp.dll"]
