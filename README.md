# dlss-combo

**DLSS 5 画质 + DLSS 帧生成，一条命令装进 RTX 20/30。**
**DLSS 5 image quality + DLSS Frame Generation, one command for RTX 20/30.**

`dlss-combo` 是一个**编排器（orchestrator）**：它把两个开源项目的成果组合到同一个游戏目录——

| 层 Layer | 项目 Project | 作用 What it does |
|---|---|---|
| 画质 Image | [DLSS5-Swapper](https://github.com/rakanki911/DLSS5-Swapper) | 安装 DLSS 5 神经渲染（ReShade/Feeder、RenoDX 路线）|
| 插帧 Frames | [dlssg_for_sm86](https://github.com/sdli1995/dlssg_for_sm86) | 在 RTX 20 (SM75) / RTX 30 (SM86) 上启用原生 DLSS-G 帧生成（最高 6X）|

`dlss-combo` is an orchestrator: it combines both open-source projects into one
game folder — DLSS5-Swapper for DLSS 5 neural rendering, dlssg_for_sm86 for
native DLSS Frame Generation on RTX 20/30.

本工具**不修改、不重编译、不分发任何上游二进制**：kit 在 `fetch` 时才从上游
官方渠道下载并做 SHA256 校验。This tool never modifies, rebuilds, or
redistributes upstream binaries; the kit is downloaded from official upstream
sources at `fetch` time and verified with SHA256.

---

## 快速开始 / Quick start

前置 / Prerequisites：Windows 10/11 x64、NVIDIA 驱动 R580+、游戏**原生支持
DLSS 帧生成（DLSS3）且为 D3D12**。仅限单机游戏。

```bash
pipx install .          # 或 python -m dlss_combo（本仓库根目录）

# 1) 下载 kit（约 180MB：dlssg 310.9 代理 + 官方 INI）
dlss-combo fetch

# 2) 画质层：用 DLSS5-Swapper 的图形界面给目标游戏装 DLSS 5 神经渲染
#    (下载其 portable 版: https://github.com/rakanki911/DLSS5-Swapper/releases)

# 3) 插帧层：把 dlssg 装进游戏目录
dlss-combo install "C:/Games/YourGame/Binaries/Win64" --arch sm86 --mfg 4x

# 4) 进游戏 → 图形设置开启 DLSS 帧生成；跑一局后体检
dlss-combo doctor "C:/Games/YourGame/Binaries/Win64"

# 卸载（还原到安装前）
dlss-combo uninstall "C:/Games/YourGame/Binaries/Win64"
```

## 命令 / Commands

| 命令 | 说明 |
|---|---|
| `fetch [--kit-dir D] [--runtime 310.9\|310.1] [--refresh]` | 下载/更新 kit 缓存（默认 `~/dlss-combo-kit`），固定到上游 commit |
| `install <game_dir> [--arch sm75\|sm86] [--mfg 2x\|3x\|4x\|6x] [--tier 0-3]` | 安装插帧层：预检 → 扫描冲突 → 选代理 → 落盘 → 校验 |
| `uninstall <game_dir>` | 按 manifest 还原安装前状态 |
| `doctor <game_dir>` | 只读体检：解析 `dlssg_sm86/logs/backend_*.jsonl` 的 `route active`，报告多代理并存、OptiScaler 双钩子、画质层状态 |

## 冲突规则（核心安全设计） / Conflict rules

代理候选序 / proxy candidates（与上游 dlssg 一致）：
`version.dll → winmm.dll → d3d12.dll → dbghelp.dll → dinput8.dll → dxgi.dll`

- **绝不覆盖非本工具安装的 DLL**——名字被占就换下一个，全被占则拒绝安装并列出清单
- `dxgi.dll` 默认不选（ReShade/OptiScaler 常用），需 `--allow-dxgi` 显式放行
- ReShade/RenoDX（DLSS 5 画质层载体）与插帧层挂钩点不同，**天然共存**；检测到
  OptiScaler 会提示"双钩子"风险
- 重装/升级：旧版本先进 `game_dir/.dlss-combo/backups/`，永远只留一个代理

## 调优指引 / Tuning

- **基础帧率决定一切**：开 4X 前请确认基础帧率 ≥ **55–60 FPS**；基础帧率太低时
  插帧伪影明显、输入延迟升高。DLSS 5 画质层会降低基础帧率，两者叠加时先测
  只开画质层的基础帧率
- `--tier`：`0` 原厂内核最保守 · `1` 逐位一致加速（默认推荐）· `2` ~50dB PSNR
  有损（仅 310.9）· `3` 全有损最快
- `--mfg 6x`：需要游戏自身支持 6X / Dynamic MFG（多数游戏上限 4X）
- 排障：`dlssg_sm86/logs/`（INI `[Logging] Level=2` 加详细度），或直接 `doctor`

## 安全警告 / Safety

- **仅限单机游戏**。带反作弊的多人游戏可能封号——两个上游项目均如此声明
- 本工具只做文件摆放；DLL 本身来自上游官方发布渠道并经 SHA256 校验
- 安装前如有其他 mod 请自行备份（本工具不触碰它们，但共存行为无法逐一保证）

## 许可 / License

- 本项目 `dlss-combo`：**MIT**
- [dlssg_for_sm86](https://github.com/sdli1995/dlssg_for_sm86)：源码 GPLv3；
  其内嵌 NVIDIA DLSS-G 运行库归 NVIDIA，本项目不分发
- [DLSS5-Swapper](https://github.com/rakanki911/DLSS5-Swapper)：MIT；由该应用
  自行管理其组件下载

## 开发 / Development

```bash
python3 -m venv .venv && .venv/bin/pip install pytest
.venv/bin/python -m pytest -v     # 67 个测试，全部离线可跑
```

架构与设计决策见 `docs/superpowers/specs/2026-09-20-dlss-combo-design.md`。
