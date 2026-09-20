"""共享测试夹具：假 kit（带真实 SHA256）与假游戏目录。"""
import json
from pathlib import Path

import pytest

ALT_NAMES = ["winmm", "d3d12", "dbghelp", "dinput8", "dxgi"]


def _kit_hashes(root: Path) -> dict[str, str]:
    from dlss_combo.manifest import Manifest

    files = {}
    for rel in ["version.dll", "dlssg_sm86.ini"] + [f"alternatives/{n}.dll" for n in ALT_NAMES]:
        files[f"dlssg/310.9/{rel}"] = Manifest.sha256_of(root / rel)
    return files


def make_kit(tmp_path: Path, version_dll: bytes = b"V9") -> Path:
    root = tmp_path / "kit" / "dlssg" / "310.9"
    (root / "alternatives").mkdir(parents=True)
    (root / "version.dll").write_bytes(version_dll)
    (root / "dlssg_sm86.ini").write_text("; upstream reference")
    for n in ALT_NAMES:
        (root / "alternatives" / f"{n}.dll").write_bytes(n.encode())
    (tmp_path / "kit" / "kit.json").write_text(
        json.dumps(
            {
                "version": 1,
                "dlssg_commits": {"310.9": "c0ffee"},
                "files": _kit_hashes(root),
            }
        )
    )
    return tmp_path / "kit"


def rehash_kit(kit_dir: Path) -> Path:
    """模拟"合法的新版本 kit"：内容变更后同步 kit.json 的哈希。"""
    root = kit_dir / "dlssg" / "310.9"
    meta = json.loads((kit_dir / "kit.json").read_text())
    meta["files"] = _kit_hashes(root)
    (kit_dir / "kit.json").write_text(json.dumps(meta))
    return kit_dir


@pytest.fixture
def kit(tmp_path: Path) -> Path:
    return make_kit(tmp_path)


@pytest.fixture
def game(tmp_path: Path) -> Path:
    g = tmp_path / "game"
    g.mkdir()
    (g / "game.exe").write_bytes(b"MZ")
    return g
