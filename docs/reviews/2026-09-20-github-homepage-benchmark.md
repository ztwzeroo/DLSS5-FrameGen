# 相关 GitHub 高关注项目 Top 10 首页对照与改版记录

日期：2026-09-20。筛选方式：GitHub 搜索 DLSS / frame generation，结合关联画质工具 Magpie、ReShade；选择 10 个相关参考仓库，在样本内按实时 API Star 数降序排列。**这是相关项目参考样本，不是 GitHub 全站或完整类目排行榜；Star 不是下载转化率，不能据此证明某种设计导致增长。**

检查了 10 份当前默认分支 README 与仓库页面；对 Magpie、DLSS5-Swapper 额外检查了浏览器渲染。迁移和冻结仓库保留在表中并单独标明，避免只看热度。

| 样本排名 | 项目 | Star 快照 | 观察到的内容结构 | 本项目采用方式 |
|---|---|---:|---|---|
| 1 | [Blinue/Magpie](https://github.com/Blinue/Magpie/blob/dev/README.md) | 14,951 | 品牌图标、英文/中文分离、下载/FAQ 导航、特性后放真实截图 | 采用独立语言入口和简洁导航；不堆双语段落 |
| 2 | [optiscaler/OptiScaler](https://github.com/optiscaler/OptiScaler/blob/master/README.md) | 11,196 | 品牌图、Stable/Nightly/Documentation 按钮、兼容表、Wiki 分流 | 采用下载/指南/反馈分流；不套用尚不存在的稳定版和下载量徽章 |
| 3 | [beeradmoore/dlss-swapper](https://github.com/beeradmoore/dlss-swapper/blob/main/README.md) | 7,476 | 居中品牌、短定位、演示 GIF、多语言入口、下载渠道说明 | 采用短定位与语言分离；待真机证据后增加实际演示 |
| 4 | [rakanki911/DLSS5-Swapper](https://github.com/rakanki911/DLSS5-Swapper/blob/main/README.md) | 5,937 | 宽幅横图、下载资产分类、产品截图、更新特性图 | 采用原创横幅；清楚写 source ZIP，不冒充 Windows installer |
| 5 | [crosire/reshade](https://github.com/crosire/reshade/blob/main/README.md) | 5,527 | 文字精炼、开发者导向、构建/API 文档与支持链接 | 借鉴清楚解释项目边界；编译细节移到贡献指南 |
| 6 | [Nukem9/dlssg-to-fsr3](https://github.com/Nukem9/dlssg-to-fsr3/blob/master/README.md) | 4,987 | 开头说明用途与兼容边界、靠前下载链接、安装方式折叠 | 采用可折叠高级命令/FAQ，基础安装保持展开 |
| 7 | [PancakeTAS/lsfg-vk](https://github.com/PancakeTAS/lsfg-vk/blob/migration/README) | 4,715 | 当前 README 是迁移告示，导向独立站及归档 | 作为状态透明的反例参考，不当作完整活跃首页模板 |
| 8 | [sdli1995/dlssg_for_sm86](https://github.com/sdli1995/dlssg_for_sm86/blob/main/README.md) | 3,556 | 开头带版本、语言切换、详细变更、显存/性能/诊断章节 | 借鉴证据定义与诊断边界；不把长更新日志挤到第一屏 |
| 9 | [emoose/DLSSTweaks](https://github.com/emoose/DLSSTweaks/blob/master/README.md) | 1,785 | 当前仓库冻结，并明确新版本的外部渠道 | 借鉴来源说明与上游署名；不复制冻结状态或捐赠入口 |
| 10 | [artur-graniszewski/DLSS-Enabler](https://github.com/artur-graniszewski/DLSS-Enabler/blob/main/README.md) | 1,350 | 用途陈述、图像、构建徽章、下载及高级说明 | 借鉴快速理解和清晰操作；不使用本项目尚不存在的 CI 徽章 |

## 改版取舍

1. 英文 README 作为默认首页；中文保留独立入口，避免中英重复使正文翻倍。
2. 用原创深色技术风格横幅说明 DLSS 5 + Frame Generation；不复制其他项目的图片、Logo 或产品截图。
3. 下载源码、安装指南、游戏反馈形成明确入口；源码下载说明与 Python 要求放在入口旁。
4. 用要求表让访客判断 GPU、系统、游戏 API 和使用条件。
5. 增加组合流程图，说明 Swapper 仍需用户操作，避免暗示全自动安装。
6. 高级命令和 FAQ 折叠；文件安全限制仍在下载前显著展示，英文详情移入 STATUS.md。
7. 增加真实证据表；没有真机游戏图和性能数据时不制作虚假 before/after 或 FPS 图。
8. 英文反馈表区分安装失败、仅文件落盘、只验证一层、两层都验证；性能数据允许不填。
9. 保留上游署名和独立社区项目说明，清楚解释我们的编排价值。
10. 已识别 CLI 输出仍有中文，将其列为后续本地化事项，首页 FAQ 如实告知。

## 仍需真实产品工作才能补齐的内容

- 完成已知文件安全、校验与回滚修复。
- 在真实 RTX 20/30 设备上录制从安装到游戏设置的短演示。
- 同场景记录原版、仅画质、仅插帧、组合四种状态，再发布图像和性能对比。
- 稳定后提供可验证的 Windows 发行包；没有发行包时不能用 Download EXE 作为按钮文案。
- 收集真实访客/克隆/发行资产下载数据后再判断转化变化；本次没有增长数据，不能承诺改版会提高下载量。

本次没有复制上游产品视觉资产，也没有使用第三方的 Star/下载量作为本项目指标。
