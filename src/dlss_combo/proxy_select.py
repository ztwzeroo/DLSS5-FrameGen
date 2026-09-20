"""选择 dlssg_for_sm86 代理 DLL 文件名的规则（纯函数）。

顺序依据上游 alternatives/README.md：根目录四个工具类代理优先
（version/winmm/dbghelp/dinput8），d3d12/dxgi 是渲染路径回退、风险更高，
排在最后且 dxgi 需显式放行。
"""
from dataclasses import dataclass

PROXY_CANDIDATES = [
    "version.dll",
    "winmm.dll",
    "dbghelp.dll",
    "dinput8.dll",
    "d3d12.dll",
    "dxgi.dll",
]
DXGI = "dxgi.dll"
D3D12 = "d3d12.dll"


@dataclass(frozen=True)
class ProxyChoice:
    name: str
    source: str  # "root" | "alternatives"


def choose_proxy(
    occupied: set[str],
    allow_dxgi: bool = False,
    force: str | None = None,
) -> ProxyChoice | None:
    """返回空闲代理名；force 显式指定（被第三方占用则拒绝返回 None）。全占用返回 None。"""
    if force is not None:
        if force not in PROXY_CANDIDATES:
            raise ValueError(f"unknown proxy name {force!r}")
        if force in occupied:
            return None
        return ProxyChoice(
            name=force, source="root" if force == "version.dll" else "alternatives"
        )
    for name in PROXY_CANDIDATES:
        if name == DXGI and not allow_dxgi:
            continue
        if name not in occupied:
            return ProxyChoice(
                name=name,
                source="root" if name == "version.dll" else "alternatives",
            )
    return None
