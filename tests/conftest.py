"""共享测试夹具：假 kit 与假游戏目录。"""
import json
from pathlib import Path

import pytest


def make_kit(tmp_path: Path, version_dll: bytes = b"V9") -> Path:
    root = tmp_path / "kit" / "dlssg" / "310.9"
    (root / "alternatives").mkdir(parents=True)
    (root / "version.dll").write_bytes(version_dll)
    (root / "dlssg_sm86.ini").write_text("; upstream reference")
    for n in ["winmm", "d3d12", "dbghelp", "dinput8", "dxgi"]:
        (root / "alternatives" / f"{n}.dll").write_bytes(n.encode())
    (tmp_path / "kit" / "kit.json").write_text(
        json.dumps({"dlssg_commit": "c0ffee", "files": {}})
    )
    return tmp_path / "kit"


@pytest.fixture
def kit(tmp_path: Path) -> Path:
    return make_kit(tmp_path)


@pytest.fixture
def game(tmp_path: Path) -> Path:
    g = tmp_path / "game"
    g.mkdir()
    (g / "game.exe").write_bytes(b"MZ")
    return g
