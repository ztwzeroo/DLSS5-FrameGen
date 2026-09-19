# dlss-combo 设计文档

**日期**: 2026-09-20
**状态**: 已批准（用户在会话中明确授权"你来做"）
**路径**: Architectural（全新项目）

## 目标

让 RTX 20/30 用户用一个命令装好"DLSS 5 画质 + DLSS 帧生成"组合方案：

- **画质层**: [DLSS5-Swapper](https://github.com/rakanki911/DLSS5-Swapper)（MIT）安装 DLSS 5 神经渲染（ReShade/Feeder、RenoDX 路线）
- **插帧层**: [dlssg_for_sm86](https://github.com/sdli1995/dlssg_for_sm86)（源码 GPLv3）在 SM75/SM86 上启用原生 DLSS-G（version.dll 代理 + dlssg_sm86.ini）

本工具是**编排器（orchestrator）**：不修改、不重编译、不分发任何上游二进制；只在安装时从上游官方渠道下载，并按冲突规则摆放文件、生成配置、管理备份与还原。

## 非目标（YAGNI）

- 不做 GUI；不做游戏数据库自动扫描全盘；不实现 DLSS5-Swapper 的组件下载逻辑（由该应用自己完成）
- 不支持 RTX 40/50 的 MFG 解锁（那是 DLSS Unlocked / AdaMfgUnlock 的领域）
- 不处理 Vulkan 游戏（dlssg_for_sm86 官方仅 D3D12，社区补丁不在范围）

## 架构

```
用户 ──> dlss-combo CLI (Python 3.10+, 纯文件操作)
          │
          ├─ fetch    ──> kit 缓存（~/dlss-combo-kit 或 --kit-dir）
          │             ├─ dlssg_for_sm86: 按固定 commit 从 raw.githubusercontent 下载
          │             │   version.dll / dlssg_sm86.ini / alternatives/*.dll（按需） + SHA256 校验
          │             └─ DLSS5-Swapper: 最新 release 的 portable zip + 官方 SHA256SUMS 校验
          │
          ├─ install <game_dir> [--mfg 4x|6x] [--tier 0..3] [--runtime 310.1|310.9]
          │    1. preflight: 平台/GPU 架构（nvidia-smi 适配器，可 --arch sm86 跳过）/驱动 ≥R580 提示
          │    2. scan: 已有代理 DLL、ReShade/Feeder/RenoDX/OptiScaler 检测 → 冲突报告
          │    3. 代理名选择: version.dll 空闲则用之；否则按 winmm→d3d12→dbghelp→dinput8→dxgi 顺序取空闲名；
          │       绝不覆盖非本工具安装的 DLL（上游多代理共存官方支持，首个加载者生效）
          │    4. 备份: 被覆盖文件移入 game_dir/.dlss-combo/backups/，记入 manifest
          │    5. 安装: 复制所选代理 DLL + 生成 dlssg_sm86.ini（tier/mfg 预设）
          │    6. 画质层: 检测 DLSS5 路线文件；缺失则提示（可选 --launch-swapper 拉起 portable exe 后复检）
          │    7. 验证: manifest 哈希 vs 磁盘文件；输出调优指引（基础帧率 ≥55–60 再开 4X/6X）
          │
          ├─ uninstall <game_dir>: 按 manifest 还原备份、删除本工具文件与清单
          │
          └─ doctor <game_dir>: 解析 dlssg_sm86/logs/backend_*.jsonl（route active），
             报告多代理并存、OptiScaler 双钩子风险、画质层缺失等
```

### 模块划分（每个可独立测试）

| 模块 | 职责 | 依赖 |
|---|---|---|
| `gpu.py` | GPU 探测适配器：nvidia-smi 解析 → sm75/sm86/unverified；接口可 mock | 无 |
| `fetch.py` | kit 下载与校验（dlssg 固定 commit；swapper 最新 release），纯标准库 urllib | 无三方依赖 |
| `scan.py` | 游戏目录扫描：代理占用、ReShade(dxgi.dll+reshade-shaders/)、RenoDX/Feeder 特征、OptiScaler | 无 |
| `proxy_select.py` | 代理名选择规则（纯函数） | scan 结果 |
| `ini.py` | dlssg_sm86.ini 生成（tier/MFG/日志预设，中英注释保留关键项） | 无 |
| `manifest.py` | `.dlss-combo/manifest.json` 读写校验（版本、来源 commit、文件 SHA256、备份索引） | 无 |
| `install.py` | 安装编排（preflight→scan→select→backup→copy→ini→verify） | 上述全部 |
| `uninstall.py` | 按 manifest 还原 | manifest |
| `doctor.py` | 日志解析 + 冲突诊断报告 | scan |
| `cli.py` | argparse 入口，子命令分发 | 全部 |

### 关键数据

**manifest.json**（放在 game_dir/.dlss-combo/，自包含可卸载）:
```json
{
  "version": 1,
  "created": "2026-09-20T…",
  "dlss_combo_version": "0.1.0",
  "dlssg": {"commit": "…", "runtime": "310.9", "proxy_name": "version.dll",
             "ini": "…生成摘要…"},
  "files": [{"path": "version.dll", "sha256": "…", "origin": "kit|backup"}],
  "backups": [{"original": "version.dll", "saved_to": ".dlss-combo/backups/version.dll.bak"}]
}
```

**kit 固定 commit**: fetch 记录 dlssg 仓库 commit 到 kit 的 `kit.json`；升级用 `fetch --refresh`。

### 冲突规则（核心领域逻辑）

1. 代理候选序: `version.dll → winmm.dll → d3d12.dll → dbghelp.dll → dinput8.dll → dxgi.dll`
2. 若候选名已被非本工具文件占用 → 跳到下一候选；全部占用 → 报错并列出现状（上游注释：多代理并存安全但冗余）
3. `dxgi.dll` 特殊性：ReShade/OptiScaler 常用它 → scan 识别后从不选它，除非其余全占用且用户 `--force`
4. 画质层与插帧层物理隔离：Swapper 路线（ReShade/RenoDX）不占 version.dll，天然共存；doctor 提示任何例外

### 错误处理

- 任何步骤失败 → 已做更改按 manifest 回滚（install 是尽力而为的事务）
- 下载校验失败 → 清理半成品，明确报错（区分网络失败 vs 哈希不符）
- doctor 无法确认 `route active=true` → 输出上游排障路径（logs 目录、INI Logging Level=2）

## 测试策略

- pytest 全覆盖：scan/proxy_select/ini/manifest/uninstall 用 tmp_path 假游戏目录；fetch 网络全部 mock（含坏哈希用例）；doctor 用样例 jsonl
- gpu.py: mock nvidia-smi 输出（RTX 3070/2080 Ti/非 N 卡/无工具 四情形）
- install 端到端（假 kit + 假目录，无网络）：含"已有 ReShade dxgi.dll"“已有第三方 version.dll"“重复安装升级”三类场景
- CI: macOS/Linux 本地 `pytest` 即全量；Windows 专属路径全部走适配器 mock

## 安全与许可

- 工具不携带任何上游二进制；安装时才下载并校验哈希（dlssg 固定 commit；swapper 官方 SHA256SUMS）
- 本项目 MIT；不包含 GPLv3 上游代码（仅调用其 release 文件）；README 明示反作弊多人游戏禁用、单机限定
- README 含调优指引：基础帧率 ≥55–60 再开 4X/6X；tier 含义；6X 需游戏自身支持

## 交付物

1. `dlss-combo` 可安装 Python 包（`pipx install` / `python -m dlss_combo`）
2. README（中英）：安装、使用、排障、与两上游项目的关系、许可声明
3. 全量测试通过 + 无网络环境验证（kit 预置时 install 可离线完成）
