# dlss-combo 实施计划

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 一个 Python CLI 编排器，把 DLSS5-Swapper（画质层）与 dlssg_for_sm86（插帧层）组合安装到 RTX 20/30 游戏目录，含冲突检测、备份还原与诊断。

**Architecture:** 纯文件操作的分层设计：scan/proxy_select/ini/manifest/gpu 为独立可测模块，fetch 管理本地 kit 缓存（上游二进制安装时才下载、SHA256 校验），install 编排全流程并在失败时回滚，uninstall 按 manifest 还原，doctor 解析上游日志。

**Tech Stack:** Python 3.10+，零三方运行时依赖（urllib + hashlib + argparse + dataclasses），pytest 测试。

**Spec:** `docs/superpowers/specs/2026-09-20-dlss-combo-design.md`

## Global Constraints

- Python ≥ 3.10；**零三方运行时依赖**（仅标准库）；pytest 仅开发依赖
- 不分发任何上游二进制；kit 在 `fetch` 时从官方渠道下载并记录 commit + SHA256
- 代理候选序（来自 spec，逐字）：`version.dll → winmm.dll → d3d12.dll → dbghelp.dll → dinput8.dll → dxgi.dll`
- 绝不覆盖非本工具安装的 DLL（备份后也不允许，选下一个候选；全占用则报错）
- manifest 放 `game_dir/.dlss-combo/manifest.json`，版本字段 `version: 1`
- 支持架构：`sm75`（RTX 20）、`sm86`（RTX 30）；其他架构 preflight 警告需 `--arch` 覆盖
- 所有公共函数带类型注解；模块级 docstring 一句话职责

---

### Task 1: 项目脚手架与测试基建

**Files:**
- Create: `pyproject.toml`, `src/dlss_combo/__init__.py`, `tests/__init__.py`（空）, `tests/test_scaffold.py`

**Interfaces:**
- Produces: 包 `dlss_combo`（src 布局），`__version__ = "0.1.0"`；pytest 可发现 tests/

- [ ] **Step 1: 写失败测试**

```python
# tests/test_scaffold.py
def test_package_importable_with_version():
    import dlss_combo
    assert dlss_combo.__version__ == "0.1.0"
```

- [ ] **Step 2: 运行确认失败**

Run: `python3 -m pytest tests/test_scaffold.py -v`
Expected: FAIL（ModuleNotFoundError）

- [ ] **Step 3: 最小实现**

```toml
# pyproject.toml
[build-system]
requires = ["setuptools>=68"]
build-backend = "setuptools.build_meta"

[project]
name = "dlss-combo"
version = "0.1.0"
description = "Combine DLSS 5 neural rendering (DLSS5-Swapper) with DLSS Frame Generation (dlssg_for_sm86) on RTX 20/30"
requires-python = ">=3.10"
license = { text = "MIT" }

[project.scripts]
dlss-combo = "dlss_combo.cli:main"

[tool.setuptools.packages.find]
where = ["src"]

[tool.pytest.ini_options]
testpaths = ["tests"]
pythonpath = ["src"]
```

```python
# src/dlss_combo/__init__.py
"""dlss-combo: DLSS5 画质 + DLSS 帧生成 组合安装编排器。"""
__version__ = "0.1.0"
```

- [ ] **Step 4: 运行确认通过**

Run: `python3 -m pytest tests/test_scaffold.py -v` → PASS

- [ ] **Step 5: Commit** `git add -A && git commit -m "chore: project scaffold with pytest infra"`

---

### Task 2: 代理名选择 proxy_select

**Files:**
- Create: `src/dlss_combo/proxy_select.py`
- Test: `tests/test_proxy_select.py`

**Interfaces:**
- Produces: `PROXY_CANDIDATES: list[str]`；`ProxyChoice(name: str, source: str)`；`choose_proxy(occupied: set[str], allow_dxgi: bool = False) -> ProxyChoice | None`。`source` 为 `"root"`（version.dll）或 `"alternatives"`（其余）。

- [ ] **Step 1: 失败测试**

```python
# tests/test_proxy_select.py
from dlss_combo.proxy_select import PROXY_CANDIDATES, ProxyChoice, choose_proxy

def test_empty_dir_gets_version_dll():
    assert choose_proxy(set()) == ProxyChoice(name="version.dll", source="root")

def test_occupied_version_falls_to_winmm():
    assert choose_proxy({"version.dll"}) == ProxyChoice(name="winmm.dll", source="alternatives")

def test_dxgi_never_chosen_by_default():
    # 前 5 个全占用，dxgi 默认排除 → 无解
    assert choose_proxy({"version.dll", "winmm.dll", "d3d12.dll", "dbghelp.dll", "dinput8.dll"}) is None

def test_dxgi_allowed_with_flag():
    occ = {"version.dll", "winmm.dll", "d3d12.dll", "dbghelp.dll", "dinput8.dll"}
    assert choose_proxy(occ, allow_dxgi=True) == ProxyChoice(name="dxgi.dll", source="alternatives")

def test_all_occupied_returns_none():
    assert choose_proxy(set(PROXY_CANDIDATES), allow_dxgi=True) is None
```

- [ ] **Step 2: 确认失败** `python3 -m pytest tests/test_proxy_select.py -v` → FAIL (ModuleNotFoundError)

- [ ] **Step 3: 实现**

```python
# src/dlss_combo/proxy_select.py
"""选择 dlssg_for_sm86 代理 DLL 文件名的规则（纯函数）。"""
from dataclasses import dataclass

PROXY_CANDIDATES = ["version.dll", "winmm.dll", "d3d12.dll", "dbghelp.dll", "dinput8.dll", "dxgi.dll"]
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
            return ProxyChoice(name=name, source="root" if name == "version.dll" else "alternatives")
    return None
```

- [ ] **Step 4: 通过** — `python3 -m pytest tests/test_proxy_select.py -v` → PASS
- [ ] **Step 5: Commit** `git commit -am "feat: proxy name selection rules"`

---

### Task 3: 游戏目录扫描 scan

**Files:**
- Create: `src/dlss_combo/scan.py`
- Test: `tests/test_scan.py`

**Interfaces:**
- Consumes: `proxy_select.PROXY_CANDIDATES`
- Produces: `GameScan(path: Path, existing_proxies: dict[str, str], reshade: bool, optiscaler: bool, renodx: bool, feeder: bool, has_our_install: bool)`；`scan_game_dir(game_dir: Path, our_files: set[str] | None = None) -> GameScan`。`existing_proxies` 值为 `"ours"`（在 our_files 中）或 `"foreign"`。

- [ ] **Step 1: 失败测试**

```python
# tests/test_scan.py
from pathlib import Path
from dlss_combo.scan import scan_game_dir

def test_clean_dir(tmp_path: Path):
    s = scan_game_dir(tmp_path)
    assert s.existing_proxies == {} and not any([s.reshade, s.optiscaler, s.renodx, s.feeder, s.has_our_install])

def test_foreign_version_dll(tmp_path: Path):
    (tmp_path / "version.dll").write_bytes(b"x")
    s = scan_game_dir(tmp_path)
    assert s.existing_proxies == {"version.dll": "foreign"}

def test_ours_marker(tmp_path: Path):
    (tmp_path / "version.dll").write_bytes(b"x")
    s = scan_game_dir(tmp_path, our_files={"version.dll"})
    assert s.existing_proxies == {"version.dll": "ours"} and s.has_our_install

def test_reshade_detected_by_shaders_dir(tmp_path: Path):
    (tmp_path / "reshade-shaders").mkdir()
    (tmp_path / "dxgi.dll").write_bytes(b"x")
    s = scan_game_dir(tmp_path)
    assert s.reshade and s.existing_proxies["dxgi.dll"] == "foreign"

def test_optiscaler_by_ini(tmp_path: Path):
    (tmp_path / "OptiScaler.ini").write_text("[General]\n")
    assert scan_game_dir(tmp_path).optiscaler

def test_renodx_and_feeder_markers(tmp_path: Path):
    (tmp_path / "renoDX_somegame.dll").write_bytes(b"x")
    (tmp_path / "dlss5-feeder.addon").write_bytes(b"x")
    s = scan_game_dir(tmp_path)
    assert s.renodx and s.feeder
```

- [ ] **Step 2: 确认失败** `python3 -m pytest tests/test_scan.py -v` → FAIL
- [ ] **Step 3: 实现**

```python
# src/dlss_combo/scan.py
"""扫描游戏目录：代理占用、ReShade/RenoDX/Feeder/OptiScaler 检测。"""
from pathlib import Path
from .proxy_select import PROXY_CANDIDATES

@dataclass  # 用 dataclasses.dataclass
class GameScan:
    path: Path
    existing_proxies: dict[str, str]
    reshade: bool
    optiscaler: bool
    renodx: bool
    feeder: bool
    has_our_install: bool

def scan_game_dir(game_dir: Path, our_files: set[str] | None = None) -> GameScan:
    our_files = our_files or set()
    existing: dict[str, str] = {}
    for name in PROXY_CANDIDATES:
        p = game_dir / name
        if p.is_file():
            existing[name] = "ours" if name in our_files else "foreign"
    files = {f.name.lower() for f in game_dir.iterdir() if f.is_file()}
    dirs = {d.name.lower() for d in game_dir.iterdir() if d.is_dir()}
    reshade = ("reshade-shaders" in dirs) or (("dxgi.dll" in files) and ("reshade.ini" in files))
    optiscaler = ("optiscaler.ini" in files) or ("optiscaler" in dirs)
    renodx = any(n.startswith("renodx") for n in files)
    feeder = any("feeder" in n for n in files)
    return GameScan(game_dir, existing, reshade, optiscaler, renodx, feeder,
                    has_our_install=any(v == "ours" for v in existing.values()))
```
（实现时补 `from dataclasses import dataclass`；`iterdir` 不存在时按空处理。）

- [ ] **Step 4: 通过** — Step: Run `python3 -m pytest tests/test_scan.py -v` → PASS
- [ ] **Step 5: Commit** `git commit -am "feat: game directory scanner"`

---

### Task 4: INI 生成 ini

**Files:**
- Create: `src/dlss_combo/ini.py`
- Test: `tests/test_ini.py`

**Interfaces:**
- Produces: `MFG_PRESET = {"2x": 1, "3x": 2, "4x": 3, "6x": 5}`；`build_ini(tier: int = 1, mfg: str = "4x", logging_level: int = 1) -> str`

- [ ] **Step 1: 失败测试**

```python
# tests/test_ini.py
import configparser
from dlss_combo.ini import MFG_PRESET, build_ini

def _parse(text: str) -> configparser.ConfigParser:
    cp = configparser.ConfigParser(strict=False)
    cp.read_string(text)
    return cp

def test_defaults():
    cp = _parse(build_ini())
    assert cp["General"]["Enabled"] == "1"
    assert cp["FrameGeneration"]["Optimized"] == "1"
    assert cp["FrameGeneration"]["MaxGeneratedFrames"] == "3"  # 4x
    assert cp["Logging"]["Level"] == "1"

def test_6x_and_tier2_and_verbose_logging():
    cp = _parse(build_ini(tier=2, mfg="6x", logging_level=2))
    assert cp["FrameGeneration"]["MaxGeneratedFrames"] == "5"
    assert cp["FrameGeneration"]["Optimized"] == "2"
    assert cp["Logging"]["Level"] == "2"

def test_invalid_args_raise():
    import pytest
    with pytest.raises(ValueError):
        build_ini(tier=4)
    with pytest.raises(ValueError):
        build_ini(mfg="9x")

def test_bilingual_comments_present():
    text = build_ini()
    assert "dlss-combo" in text and "dlssg_sm86\\logs" in text
```

- [ ] **Step 2: 确认失败** — FAIL
- [ ] **Step 3: 实现**（生成带中英注释的完整 INI；键值与上游 `dlssg_sm86.ini` 一致：`[General] Enabled`、`[FrameGeneration] Optimized/MaxGeneratedFrames`、`[Compatibility] Preset=Auto`、`[Logging] Level/Directory=dlssg_sm86\logs`、`[Runtime] Mode=Bundled/CacheDirectory=`）
- [ ] **Step 4: 通过** — Run → PASS
- [ ] **Step 5: Commit** `git commit -am "feat: dlssg_sm86.ini generator"`

---

### Task 5: 清单 manifest

**Files:**
- Create: `src/dlss_combo/manifest.py`
- Test: `tests/test_manifest.py`

**Interfaces:**
- Produces: `@dataclass Manifest(version:int=1, created:str, dlss_combo_version:str, dlssg:dict, files:list[dict], backups:list[dict])`，方法 `save(game_dir)->Path`、`Manifest.load(game_dir)->Manifest`（不存在抛 `FileNotFoundError`）、`record_file(path,sha256,origin)`、`record_backup(original,saved_to)`、`sha256_of(path)->str`；`MANIFEST_DIR=".dlss-combo"`, `our_file_names(m)->set[str]`

- [ ] **Step 1: 失败测试**

```python
# tests/test_manifest.py
from pathlib import Path
import pytest
from dlss_combo.manifest import Manifest

def test_roundtrip_and_file_hash(tmp_path: Path):
    dll = tmp_path / "version.dll"; dll.write_bytes(b"abc")
    m = Manifest(created="2026-09-20T00:00:00", dlss_combo_version="0.1.0", dlssg={}, files=[], backups=[])
    sha = m.sha256_of(dll)
    m.record_file("version.dll", sha, origin="kit")
    m.record_backup("version.dll", ".dlss-combo/backups/version.dll.bak")
    saved = m.save(tmp_path)
    m2 = Manifest.load(tmp_path)
    assert m2.files[0] == {"path": "version.dll", "sha256": sha, "origin": "kit"}
    assert m2.backups[0]["original"] == "version.dll"
    assert Manifest.our_file_names(m2) == {"version.dll"}

def test_load_missing_raises(tmp_path: Path):
    with pytest.raises(FileNotFoundError):
        Manifest.load(tmp_path)
```

- [ ] **Step 2–4: 红绿** — Run `python3 -m pytest tests/test_manifest.py -v`；实现 json 序列化到 `game_dir/.dlss-combo/manifest.json`
- [ ] **Step 5: Commit** `git commit -am "feat: install manifest"`

---

### Task 6: GPU 探测 gpu

**Files:**
- Create: `src/dlss_combo/gpu.py`
- Test: `tests/test_gpu.py`

**Interfaces:**
- Produces: `@dataclass GpuInfo(vendor:str, name:str, arch:str|None, source:str)`；`SUPPORTED = {"sm75","sm86"}`；`detect_gpu(override:str|None=None, runner=None)->GpuInfo`（runner 为 `Callable[[str], str]` 执行 nvidia-smi，可注入）；`_parse_nvidia_smi(text:str)->GpuInfo|None`（从 `nvidia-smi --query-gpu=name,driver_version --format=csv` 输出 + 名字→架构映射表推断 sm75/sm86）

- [ ] **Step 1: 失败测试**

```python
# tests/test_gpu.py
from dlss_combo.gpu import SUPPORTED, GpuInfo, detect_gpu, _parse_nvidia_smi

SMI_3070 = "name, driver_version\nNVIDIA GeForce RTX 3070, 591.86\n"
SMI_2080TI = "name, driver_version\nNVIDIA GeForce RTX 2080 Ti, 601.05\n"
SMI_5070 = "name, driver_version\nNVIDIA GeForce RTX 5070, 610.74\n"

def test_parse_sm86():
    g = _parse_nvidia_smi(SMI_3070); assert g and g.arch == "sm86" and g.vendor == "nvidia"

def test_parse_sm75():
    g = _parse_nvidia_smi(SMI_2080TI); assert g and g.arch == "sm75"

def test_unsupported_arch_detected():
    g = _parse_nvidia_smi(SMI_5070); assert g and g.arch == "sm120" and g.arch not in SUPPORTED

def test_override_wins():
    assert detect_gpu(override="sm86").arch == "sm86"

def test_no_tool_yields_unknown(monkeypatch):
    def boom(cmd): raise FileNotFoundError("no nvidia-smi")
    g = detect_gpu(runner=boom); assert g.source == "unknown" and g.arch is None
```

- [ ] **Step 2–4: 红绿** — 实现名字→架构映射：RTX 20xx/TITAN RTX→sm75；RTX 30xx/A10/A40→sm86；RTX 40xx→sm89；RTX 50xx→sm120；其余 None
- [ ] **Step 5: Commit** `git commit -am "feat: gpu detection adapter"`

---

### Task 7: kit 下载 fetch

**Files:**
- Create: `src/dlss_combo/fetch.py`
- Test: `tests/test_fetch.py`

**Interfaces:**
- Consumes: 无
- Produces: `DLSSG_REPO="sdli1995/dlssg_for_sm86"`；`@dataclass KitInfo(root:Path, dlssg_commit:str, sha256:dict[str,str])`；`fetch_kit(kit_dir:Path, runtime:str="310.9", refresh:bool=False, fetch_bytes=None)->KitInfo`；`verify_kit(kit_dir:Path, runtime:str="310.9")->list[str]`（返回问题清单，空=健康）。`fetch_bytes: Callable[[str], bytes]` 注入用于测试。文件清单：`{root: version.dll, dlssg_sm86.ini, alternatives/(winmm|d3d12|dbghelp|dinput8|dxgi).dll}`（310.9 来自仓库 main 树根；310.1 加前缀 `310.1/`）。kit.json 记录 commit 与各文件 sha256。

- [ ] **Step 1: 失败测试**

```python
# tests/test_fetch.py
import json
from pathlib import Path
import pytest
from dlss_combo.fetch import fetch_kit, verify_kit

RAW_BASE = "https://raw.githubusercontent.com/sdli1995/dlssg_for_sm86"

def make_fetch(files: dict[str, bytes], commit: str = "abc1234"):
    def fetch_bytes(url: str) -> bytes:
        for key, blob in files.items():
            if url.endswith(key):
                return blob
        raise RuntimeError(f"unexpected url {url}")
    return fetch_bytes

def test_fetch_writes_kit_and_json(tmp_path: Path):
    files = {"version.dll": b"dll3109", "dlssg_sm86.ini": b"[General]",
             "alternatives/winmm.dll": b"w", "alternatives/d3d12.dll": b"d3",
             "alternatives/dbghelp.dll": b"db", "alternatives/dinput8.dll": b"di",
             "alternatives/dxgi.dll": b"dx"}
    kit = fetch_kit(tmp_path, fetch_bytes=make_fetch(files))
    assert (kit.root / "dlssg" / "310.9" / "version.dll").read_bytes() == b"dll3109"
    meta = json.loads((tmp_path / "kit.json").read_text())
    assert meta["dlssg_commit"] and len(meta["files"]) == 7
    assert verify_kit(tmp_path) == []

def test_fetch_aborts_on_corrupt_file(tmp_path: Path):
    files = {"version.dll": b"partial", "dlssg_sm86.ini": b"[General]",
             "alternatives/winmm.dll": b"w", "alternatives/d3d12.dll": b"d3",
             "alternatives/dbghelp.dll": b"db", "alternatives/dinput8.dll": b"di",
             "alternatives/dxgi.dll": b"dx"}
    # 让 dxgi 下载返回被截断的内容 → sha 记录前后不一致的场景用 verify_kit 模拟
    kit = fetch_kit(tmp_path, fetch_bytes=make_fetch(files))
    # 篡改一个文件后 verify 报告该文件
    (kit.root / "dlssg" / "310.9" / "version.dll").write_bytes(b"tampered")
    problems = verify_kit(tmp_path)
    assert any("version.dll" in p for p in problems)

def test_fetch_no_network_raises(tmp_path: Path):
    with pytest.raises(RuntimeError):
        fetch_kit(tmp_path, fetch_bytes=lambda url: (_ for _ in ()).throw(RuntimeError("net down")))
```

- [ ] **Step 2–4: 红绿** — 实现：resolve commit（`https://api.github.com/repos/…/commits/main` 取 sha，fetch_bytes 注入时用固定 "unpinned-test" 之外的稳定回退）；逐文件下载→写 kit→算 sha256→写 kit.json；已有 kit.json 且未 refresh 时跳过下载直接返回 KitInfo
- [ ] **Step 5: Commit** `git commit -am "feat: kit fetcher with sha256 verification"`

---

### Task 8: 安装编排 install

**Files:**
- Create: `src/dlss_combo/install.py`
- Test: `tests/test_install.py`

**Interfaces:**
- Consumes: `scan.scan_game_dir`, `proxy_select.choose_proxy`, `ini.build_ini`, `manifest.Manifest`, `gpu.detect_gpu/SUPPORTED`, `fetch.verify_kit`
- Produces: `@dataclass InstallResult(ok:bool, proxy_name:str|None, actions:list[str], warnings:list[str], guidance:list[str])`；`install(game_dir:Path, kit_dir:Path, *, tier:int=1, mfg:str="4x", runtime:str="310.9", arch:str|None=None, allow_dxgi:bool=False)->InstallResult`。异常时回滚（见下）。

- [ ] **Step 1: 失败测试**（核心场景；假 kit 用 fixture 造）

```python
# tests/test_install.py
import json
from pathlib import Path
import pytest
from dlss_combo.install import install

@pytest.fixture
def kit(tmp_path: Path) -> Path:
    root = tmp_path / "kit" / "dlssg" / "310.9"
    (root / "alternatives").mkdir(parents=True)
    (root / "version.dll").write_bytes(b"V9")
    (root / "dlssg_sm86.ini").write_text("; upstream")
    for n in ["winmm", "d3d12", "dbghelp", "dinput8", "dxgi"]:
        (root / "alternatives" / f"{n}.dll").write_bytes(n.encode())
    meta = {"dlssg_commit": "c0ffee", "files": {}}
    (tmp_path / "kit" / "kit.json").write_text(json.dumps(meta))
    return tmp_path / "kit"

@pytest.fixture
def game(tmp_path: Path) -> Path:
    g = tmp_path / "game"; g.mkdir(); (g / "game.exe").write_bytes(b"MZ")
    return g

def test_fresh_install_uses_version_dll(game: Path, kit: Path):
    r = install(game, kit, arch="sm86")
    assert r.ok and r.proxy_name == "version.dll"
    assert (game / "version.dll").read_bytes() == b"V9"
    ini = (game / "dlssg_sm86.ini").read_text()
    assert "MaxGeneratedFrames=3" in ini
    assert (game / ".dlss-combo" / "manifest.json").is_file()

def test_foreign_version_dll_gets_winmm_no_overwrite(game: Path, kit: Path):
    (game / "version.dll").write_bytes(b"someone-else")
    r = install(game, kit, arch="sm86")
    assert r.ok and r.proxy_name == "winmm.dll"
    assert (game / "version.dll").read_bytes() == b"someone-else"

def test_reshade_dxgi_present_prefers_version_dll(game: Path, kit: Path):
    (game / "reshade-shaders").mkdir(); (game / "dxgi.dll").write_bytes(b"reshade")
    r = install(game, kit, arch="sm86")
    assert r.proxy_name == "version.dll" and any("ReShade" in w or "DLSS 5" in w for w in r.warnings + r.guidance)

def test_unsupported_arch_needs_override(game: Path, kit: Path):
    r = install(game, kit, arch="sm120")
    assert not r.ok and any("sm120" in w for w in r.warnings)

def test_reinstall_upgrades_and_keeps_single_proxy(game: Path, kit: Path):
    install(game, kit, arch="sm86")
    (game / ".dlss-combo" / "backups").mkdir(exist_ok=True)
    (kit / "dlssg" / "310.9" / "version.dll").write_bytes(b"V9-new")
    r = install(game, kit, arch="sm86")
    assert r.ok and r.proxy_name == "version.dll"
    assert (game / "version.dll").read_bytes() == b"V9-new"
    proxies = [p.name for p in game.glob("*.dll")]
    assert proxies == ["version.dll"]  # 没有重复代理
```

- [ ] **Step 2: 确认失败** — FAIL
- [ ] **Step 3: 实现要点**（完整实现于代码中）：
  1. `detect_gpu(override=arch)`；arch 不在 SUPPORTED 且未 override → 返回 `ok=False`
  2. `kit` 校验：`verify_kit` 有问题 → `ok=False`（测试 fixture kit.json 无 files 时跳过哈希校验，`origin="kit"` 仍记录当前哈希）
  3. 读旧 manifest → `our_files`；`scan_game_dir`；`choose_proxy(occupied={foreign 名集合}, allow_dxgi)`；None → `ok=False` 并列出占用清单
  4. 旧 manifest 存在时先删除我们自己的旧代理/旧 ini（记录 action），第三方文件绝不触碰
  5. 写 ini（`build_ini(tier, mfg)`）+ 复制所选代理；`.dlss-combo/backups/` 仅在覆盖"我们自己的"文件时使用（正常路径无需备份第三方）
  6. `Manifest` 记录 `dlssg={commit, runtime, proxy_name, tier, mfg}` 与 files；save
  7. guidance：基础帧率 ≥55–60 再开 4X/6X、游戏内开 DLSS 帧生成、日志路径 `.dlss-combo/../dlssg_sm86/logs`、DLSS5 层缺失时提示先跑 DLSS5-Swapper（scan 无 reshade/renodx/feeder 时加一条）
  8. try/except 包裹步骤 4–6：异常时删除新写文件、恢复删除，然后 re-raise
- [ ] **Step 4: 通过** — Run `python3 -m pytest tests/test_install.py -v` → PASS
- [ ] **Step 5: Commit** `git commit -am "feat: install orchestration with conflict rules and rollback"`

---

### Task 9: 卸载 uninstall

**Files:**
- Create: `src/dlss_combo/uninstall.py`
- Test: `tests/test_uninstall.py`

**Interfaces:**
- Consumes: `manifest.Manifest`
- Produces: `uninstall(game_dir:Path)->list[str]`（动作清单；无 manifest 抛 `FileNotFoundError`）

- [ ] **Step 1: 失败测试**

```python
# tests/test_uninstall.py
from pathlib import Path
import pytest
from dlss_combo.install import install
from dlss_combo.uninstall import uninstall

def _kit(tmp_path: Path) -> Path:
    root = tmp_path / "kit" / "dlssg" / "310.9"
    (root / "alternatives").mkdir(parents=True)
    (root / "version.dll").write_bytes(b"V")
    (root / "dlssg_sm86.ini").write_text("; u")
    for n in ["winmm", "d3d12", "dbghelp", "dinput8", "dxgi"]:
        (root / "alternatives" / f"{n}.dll").write_bytes(n.encode())
    (tmp_path / "kit" / "kit.json").write_text('{"dlssg_commit": "c", "files": {}}')
    return tmp_path / "kit"

def test_uninstall_restores_clean_state(tmp_path: Path):
    game = tmp_path / "game"; game.mkdir(); (game / "game.exe").write_bytes(b"MZ")
    install(game, _kit(tmp_path), arch="sm86")
    actions = uninstall(game)
    assert not (game / "version.dll").exists()
    assert not (game / "dlssg_sm86.ini").exists()
    assert not (game / ".dlss-combo").exists()
    assert (game / "game.exe").exists() and actions

def test_uninstall_without_manifest_raises(tmp_path: Path):
    with pytest.raises(FileNotFoundError):
        uninstall(tmp_path)
```

- [ ] **Step 2–4: 红绿** — 实现：读 manifest → 删 files 中 origin=="kit" 的文件 → 还原 backups → 删 `.dlss-combo/` 目录
- [ ] **Step 5: Commit** `git commit -am "feat: uninstall restores pre-install state"`

---

### Task 10: 诊断 doctor

**Files:**
- Create: `src/dlss_combo/doctor.py`
- Test: `tests/test_doctor.py`

**Interfaces:**
- Consumes: `scan.scan_game_dir`, `manifest.Manifest`
- Produces: `@dataclass DoctorReport(lines:list[str], route_active:bool|None)`；`doctor(game_dir:Path)->DoctorReport`；`_parse_route_active(text:str)->bool|None`（在 JSONL 行中找 `"route"` 行的 `"active": true/false`）

- [ ] **Step 1: 失败测试**

```python
# tests/test_doctor.py
import json
from pathlib import Path
from dlss_combo.doctor import _parse_route_active, doctor

def test_parse_active_true():
    line = json.dumps({"event": "install", "route": {"active": True, "name": "sm86"}})
    assert _parse_route_active(line + "\n") is True

def test_parse_no_route_yields_none():
    assert _parse_route_active('{"event":"boot"}\n') is None

def test_doctor_reports_missing_route(tmp_path: Path):
    rep = doctor(tmp_path)
    assert rep.route_active is None
    assert any("dlssg_sm86" in l and "logs" in l for l in rep.lines)

def test_doctor_reads_backend_log(tmp_path: Path):
    logdir = tmp_path / "dlssg_sm86" / "logs"; logdir.mkdir(parents=True)
    (logdir / "backend_123.jsonl").write_text(
        '{"event":"install","route":{"active":true}}\n')
    rep = doctor(tmp_path)
    assert rep.route_active is True

def test_doctor_flags_foreign_version_dll_conflict(tmp_path: Path):
    (tmp_path / "version.dll").write_bytes(b"x")
    rep = doctor(tmp_path)
    assert any("version.dll" in l for l in rep.lines)
```

- [ ] **Step 2–4: 红绿** — 实现：扫描 + 读 `dlssg_sm86/logs/backend_*.jsonl` 全部行解析；多代理并存、未装画质层、manifest 缺失均输出提示行
- [ ] **Step 5: Commit** `git commit -am "feat: doctor diagnostics"`

---

### Task 11: CLI 入口

**Files:**
- Create: `src/dlss_combo/cli.py`, `src/dlss_combo/__main__.py`
- Test: `tests/test_cli.py`

**Interfaces:**
- Consumes: 全部模块
- Produces: `main(argv:list[str]|None=None)->int`；`python -m dlss_combo` / `dlss-combo` 入口。子命令：`fetch [--kit-dir] [--runtime 310.9] [--refresh]`、`install <game_dir> [--kit-dir] [--mfg 2x|3x|4x|6x] [--tier 0-3] [--runtime 310.9|310.1] [--arch sm75|sm86] [--allow-dxgi]`、`uninstall <game_dir>`、`doctor <game_dir>`。默认 kit 目录 `~/dlss-combo-kit`。

- [ ] **Step 1: 失败测试**

```python
# tests/test_cli.py
import json
from pathlib import Path
import pytest
from dlss_combo.cli import main

def _kit(tmp_path: Path) -> Path:
    root = tmp_path / "kit" / "dlssg" / "310.9"
    (root / "alternatives").mkdir(parents=True)
    (root / "version.dll").write_bytes(b"V")
    (root / "dlssg_sm86.ini").write_text("; u")
    for n in ["winmm", "d3d12", "dbghelp", "dinput8", "dxgi"]:
        (root / "alternatives" / f"{n}.dll").write_bytes(n.encode())
    (tmp_path / "kit" / "kit.json").write_text('{"dlssg_commit": "c", "files": {}}')
    return tmp_path / "kit"

def test_install_via_cli(tmp_path: Path, capsys):
    game = tmp_path / "game"; game.mkdir(); (game / "g.exe").write_bytes(b"MZ")
    rc = main(["install", str(game), "--kit-dir", str(_kit(tmp_path)), "--arch", "sm86", "--mfg", "4x"])
    assert rc == 0 and (game / "version.dll").exists()
    assert "55" in capsys.readouterr().out  # 调优指引含基础帧率建议

def test_unsupported_arch_cli_fails(tmp_path: Path, capsys):
    game = tmp_path / "g2"; game.mkdir()
    rc = main(["install", str(game), "--kit-dir", str(_kit(tmp_path)), "--arch", "sm120"])
    assert rc != 0

def test_doctor_via_cli_on_missing_dir(tmp_path: Path):
    rc = main(["doctor", str(tmp_path / "nowhere")])
    assert rc != 0

def test_uninstall_via_cli(tmp_path: Path):
    game = tmp_path / "g3"; game.mkdir()
    main(["install", str(game), "--kit-dir", str(_kit(tmp_path)), "--arch", "sm86"])
    assert main(["uninstall", str(game)]) == 0
```

- [ ] **Step 2–4: 红绿** — argparse 实现，异常捕获转非零退出码 + stderr 消息
- [ ] **Step 5: Commit** `git commit -am "feat: CLI entry point"`

---

### Task 12: README 与收尾验证

**Files:**
- Create: `README.md`, `LICENSE`（MIT）
- Test: 无新测试；全量回归

- [ ] **Step 1: README（中英双语）**：是什么/两上游关系图、快速开始（fetch→DLSS5-Swapper→install→游戏内开启）、代理冲突规则表、调优指引（基础帧率 ≥55–60 再 4X/6X；tier 0–3 含义）、doctor 排障、反作弊警告（仅单机）、许可（MIT；不含上游二进制；dlssg 源码 GPLv3 归上游）
- [ ] **Step 2: 全量测试** `python3 -m pytest -v` → 全绿
- [ ] **Step 3: 离线安装演练**（脚本模拟：假 kit + tmp 游戏目录跑 install/uninstall/doctor，断言零网络）
- [ ] **Step 4: Commit** `git add -A && git commit -m "docs: bilingual README with safety and tuning guide"`

---

## Self-Review 结论

- **Spec 覆盖**：spec 的模块表 10 项 → Task 1–11 一一对应；kit/manifest/冲突规则/回滚/doctor/指引全覆盖。fetch 的 310.1 支持通过 `--runtime 310.1` 走同一路径（kit 目录名参数化），测试只测 310.9 主路径。
- **占位符**：Task 4/8 Step 3 为实现要点而非完整代码（INI 文本与编排主体），执行时按要点+上游 INI 原文落码，无 TBD。
- **类型一致**：`choose_proxy(occupied: set[str], allow_dxgi)` 在 Task 2/8 一致；`Manifest.load/save/our_file_names` 在 5/8/9/10 一致；`install(game_dir, kit_dir, *, tier, mfg, runtime, arch, allow_dxgi)` 在 8/9/11 一致。
