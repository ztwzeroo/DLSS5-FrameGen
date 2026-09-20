[English](README.md) · **简体中文**

<div align="center">

# DLSS5-FrameGen

### DLSS 5 + 插帧，让 RTX 20/30 探索更多可能
### DLSS 5 + Frame Generation for RTX 20/30

**A community toolkit combining DLSS5-Swapper and dlssg_for_sm86.**
**把 DLSS 5 画质工具与 DLSS 帧生成整合到一个工作流。**

[![Status: Experimental](https://img.shields.io/badge/status-experimental-orange)](#project-status--项目状态)
[![Python 3.10+](https://img.shields.io/badge/python-3.10%2B-blue)](https://www.python.org/downloads/)
[![Target: Windows](https://img.shields.io/badge/target-Windows-0078D6)](#requirements--运行条件)
[![License: MIT](https://img.shields.io/badge/license-MIT-green)](LICENSE)

**下载 / Download**: [Releases](https://github.com/ztwzeroo/DLSS5-FrameGen/releases) 提供
Windows EXE 与 Linux x64 二进制（GitHub Actions 从打 tag 的提交构建，未签名），
也可 `pipx install git+https://github.com/ztwzeroo/DLSS5-FrameGen.git` 从源码运行。

> Linux/Steam Proton（实验性）：用 Steam“浏览本地文件”定位含渲染 EXE 的实际目录；
> 启动选项 `WINEDLLOVERRIDES="version=n,b" PROTON_ENABLE_NVAPI=1 …` 为社区惯例、未经本组合实测。
> Linux 包需 glibc ≥ 2.35（Ubuntu 22.04 构建，实测下限见包内 build-info.txt）。

[How it works / 工作原理](#how-it-works--工作原理) · [Getting started / 开始使用](#getting-started--开始使用) · [Known issues / 已知问题](docs/reviews/2026-09-20-project-review.md) · [Report results / 反馈实测](https://github.com/ztwzeroo/DLSS5-FrameGen/issues)

</div>

## Project status / 项目状态

> **Experimental developer preview — not a stable installer.**
> **实验性开发预览，尚非稳定安装器。**
>
> 107 offline tests pass, and the Python wheel builds successfully. Windows/NVIDIA game testing, image quality, FPS gains and combined compatibility have **not yet been validated by this project**.
>
> 已通过 107 个离线测试与 Python 包构建检查；本项目尚未完成 Windows/NVIDIA 游戏实测，画质、帧率提升和组合稳定性均待验证。
>
> The [project audit](docs/reviews/2026-09-20-project-review.md) identifies unresolved file deletion, backup/restore and checksum issues. Use disposable test directories or separately backed-up game copies. Do not rely on this version's uninstall command as your only recovery method.
>
> [项目审查](docs/reviews/2026-09-20-project-review.md)发现尚未修复的文件删除、备份还原和哈希校验问题。当前请使用可丢弃的测试目录或独立备份的游戏副本，不要把本版本的卸载功能作为唯一恢复手段。

## How it works / 工作原理

| Layer / 层 | Upstream project / 上游项目 | Role / 作用 |
|---|---|---|
| Image / 画质 | [DLSS5-Swapper](https://github.com/rakanki911/DLSS5-Swapper) | Manages DLSS 5 installation routes, including ReShade/Feeder and RenoDX / 管理 DLSS 5 画质层安装路线 |
| Frames / 插帧 | [dlssg_for_sm86](https://github.com/sdli1995/dlssg_for_sm86) | Provides the DLSS-G proxy targeting RTX 20/30 / 提供面向 RTX 20/30 的 DLSS-G 插帧代理 |
| Workflow / 编排 | **DLSS5-FrameGen** | Downloads components, selects a proxy, generates INI settings, records installed files and reads diagnostics / 下载组件、选择代理、生成配置、记录安装清单和读取诊断 |

This project is an **orchestrator**, not a rendering implementation. It does not modify, rebuild or bundle upstream binaries. Components are downloaded from upstream repositories when you run `fetch`. DLSS5-Swapper's own interface is still needed to configure the image layer.

本项目是**组合编排工具**，渲染能力来自上游项目。仓库不携带上游 DLL 或 EXE；运行 `fetch` 时才下载。画质层仍需在 DLSS5-Swapper 界面中操作，文件放置成功也不等于游戏内效果已经生效。

Independent community project. Not affiliated with or endorsed by NVIDIA or the upstream maintainers. DLSS and RTX are NVIDIA trademarks.

## Features / 当前功能

- **Component downloads / 组件下载** — dlssg runtime 310.9 or 310.1, plus DLSS5-Swapper portable.
- **Proxy selection / 代理选择** — chooses an available candidate filename; avoids `dxgi.dll` by default.
- **Frame-generation settings / 插帧配置** — 2X / 3X / 4X / 6X ceilings and tier 0–3. Actual behavior depends on the runtime and game; 6X requires a compatible 310.9 build and game.
- **Install records / 安装记录** — manifest and backups, with safety fixes tracked in the audit.
- **Diagnostics / 诊断** — file integrity checks and backend logs. Current detection has known limitations; see the audit.
- **Offline development tests / 离线开发测试** — mock downloads, GPUs and game folders without loading real binaries.

## Requirements / 运行条件

Target environment: **Windows 10/11 x64, RTX 20 or RTX 30**, and a D3D12 game with native DLSS Frame Generation support. Check the upstream project's current driver requirements; this tool uses R580 as its warning threshold. Python 3.10+ is required for the CLI.

目标环境为 **Windows 10/11 x64、RTX 20/30**，游戏需原生支持 DLSS 帧生成并使用 D3D12。驱动要求请参照上游说明，本工具以 R580 为警告阈值。命令行工具需要 Python 3.10+。

**Single-player testing only. Do not use with anti-cheat or competitive multiplayer games.**
**仅限单机测试，不要用于带反作弊的游戏或竞技多人游戏。**

## Getting started / 开始使用

The commands below are for experimental testing. Read the known issues and keep an independent backup before writing to any game directory.

以下命令供实验测试使用。向游戏目录写入前，请先阅读已知问题并保留独立备份。

```powershell
git clone https://github.com/ztwzeroo/DLSS5-FrameGen.git
cd DLSS5-FrameGen
py -m pip install .

# Download upstream components / 下载上游组件
dlss-combo fetch

# Configure the image layer in DLSS5-Swapper first.
# 先使用下载的 DLSS5-Swapper 给测试游戏副本配置画质层。

# Install the frame-generation layer beside the rendering EXE.
# 将插帧层安装到测试副本的实际渲染 EXE 所在目录。
dlss-combo install "C:/Games/TestCopy/Binaries/Win64" --mfg 4x

# After playing, inspect logs / 运行游戏后读取诊断
dlss-combo doctor "C:/Games/TestCopy/Binaries/Win64"
```

The command remains **`dlss-combo`**; the public project name is **DLSS5-FrameGen**. Use `py -m dlss_combo` after installation if the command is not on your PATH.

公开项目名为 **DLSS5-FrameGen**，现有命令保持 **`dlss-combo`**。如果找不到命令，安装后可使用 `py -m dlss_combo`。

| Command / 命令 | Purpose / 用途 |
|---|---|
| `fetch [--runtime 310.9\|310.1] [--kit-dir DIR] [--refresh]` | Download components; default cache is `~/dlss-combo-kit` / 下载组件 |
| `install DIR [--mfg 2x\|3x\|4x\|6x] [--tier 0-3] [--runtime 310.9\|310.1] [--kit-dir DIR]` | Install the frame-generation layer / 安装插帧层 |
| `install DIR --arch sm75\|sm86` | Override GPU detection; currently also bypasses driver detection / 覆盖 GPU 探测，当前也会跳过驱动探测 |
| `install DIR --launch-swapper` | Open the cached Swapper asset; launch validation improvements are pending / 打开缓存的 Swapper，启动校验待完善 |
| `doctor DIR` | Inspect files and available logs / 读取文件与日志状态 |
| `uninstall DIR` | Remove managed files; restoration limitations remain / 卸载本工具文件，还原能力存在已知限制 |

ReShade, RenoDX or Feeder file markers alone do not prove DLSS 5 is active. Coexistence with other mods depends on the game and installation route. Measure the base frame rate before raising the frame-generation multiplier.

检测到 ReShade、RenoDX 或 Feeder 文件不代表 DLSS 5 已生效。与其他 mod 是否兼容取决于具体游戏和安装路线；提高插帧倍数前，请先测不插帧时的基础帧率。

## Roadmap / 改善路线

- [ ] Safe file ownership, bounded uninstall paths and original configuration restoration / 文件归属、卸载范围和原始配置还原。
- [ ] Reliable rollback and strict checksum validation / 完整回滚与严格哈希校验。
- [ ] Transactional downloads and per-runtime version records / 下载失败保护与运行库独立版本记录。
- [ ] Accurate session diagnostics and install previews / 准确诊断与安装预览。
- [ ] Windows tests and a reproducible RTX 20/30 game compatibility matrix / Windows 测试与可复现的游戏兼容性表。

Contributions focused on these items and reproducible game reports are welcome. Please distinguish file installation success from in-game activation and measured performance.

欢迎参与上述修复，也欢迎提交可复现的游戏测试记录。请区分“文件已安装”“游戏内已生效”和“性能已经测量”。

## Report results / 反馈实测

[Open an issue](https://github.com/ztwzeroo/DLSS5-FrameGen/issues/new/choose) with your game and version, GPU, driver, Windows version, upstream component versions, runtime, proxy filename and settings. Include the exact steps and relevant logs. For performance reports, compare the original game, image layer only, frame generation only and both combined using the same scene and settings. Remove personal paths and account information from logs before sharing.

反馈时请附游戏与版本、显卡、驱动、Windows 版本、组件版本、运行库、代理名、配置和复现步骤。性能对比请采用同一场景与设置，分别测试原版、仅画质层、仅插帧、两者组合。

## Development / 开发

```powershell
py -m venv .venv
.venv\Scripts\python -m pip install -e . pytest
.venv\Scripts\python -m pytest -q
```

On macOS/Linux, use `python3` and `.venv/bin/python`. Tests use simulated files and GPUs; they do not demonstrate Windows runtime compatibility.

- [Architecture / 架构设计](docs/superpowers/specs/2026-09-20-dlss-combo-design.md)
- [Audit and acceptance criteria / 审查与验收标准](docs/reviews/2026-09-20-project-review.md)
- [Isolated issue reproductions / 隔离问题复现](docs/reviews/2026-09-20-repro.py)

The audit reproduction script checks that known problem behaviors can be reproduced; a successful run is **not** a safety approval. Design documents describe intended behavior; the audit records current implementation gaps.

## Credits & license / 致谢与许可

Thanks to the maintainers of [DLSS5-Swapper](https://github.com/rakanki911/DLSS5-Swapper) and [dlssg_for_sm86](https://github.com/sdli1995/dlssg_for_sm86). Their projects provide the rendering and frame-generation capabilities; this repository provides the integration workflow.

本项目代码采用 [MIT License](LICENSE)。上游组件保留各自的许可和使用条款，本仓库不分发它们的二进制文件。
