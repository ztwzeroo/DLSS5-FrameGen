"""选择 dlssg_for_sm86 代理 DLL 文件名的规则（纯函数）。"""
from dataclasses import dataclass

PROXY_CANDIDATES = [
    "version.dll",
    "winmm.dll",
    "d3d12.dll",
    "dbghelp.dll",
    "dinput8.dll",
    "dxgi.dll",
]
DXGI = "dxgi.dll"


@dataclass(frozen=True)
class ProxyChoice:
    name: str
    source: str  # "root" | "alternatives"


def choose_proxy(occupied: set[str], allow_dxgi: bool = False) -> ProxyChoice | None:
    """返回第一个空闲代理名；dxgi 默认排除（ReShade/OptiScaler 常用）。全占用返回 None。"""
    for name in PROXY_CANDIDATES:
        if name == DXGI and not allow_dxgi:
            continue
        if name not in occupied:
            return ProxyChoice(
                name=name,
                source="root" if name == "version.dll" else "alternatives",
            )
    return None
