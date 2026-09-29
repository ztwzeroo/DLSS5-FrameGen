<p align="center">
  <img src="assets/hero.svg" alt="DLSS5-FrameGen: DLSS 5 meets Frame Generation. Experimental community toolkit targeting RTX 20 and RTX 30." width="100%">
</p>

<p align="center">
  <strong>English</strong> · <a href="README.zh-CN.md">简体中文</a>
</p>

# DLSS 5 + Frame Generation for RTX 20/30

**Explore DLSS 5 and frame generation together, with a shared setup workflow.** DLSS5-FrameGen connects [DLSS5-Swapper](https://github.com/rakanki911/DLSS5-Swapper) and [dlssg_for_sm86](https://github.com/sdli1995/dlssg_for_sm86): download components, configure the frame-generation layer, and inspect the resulting logs.

[![Stage: Developer preview](https://img.shields.io/badge/stage-developer_preview-e8b35a?style=flat-square)](docs/STATUS.md)
[![Target: Windows](https://img.shields.io/badge/target-Windows_10%2F11-334234?style=flat-square)](#will-it-work-with-my-setup)
[![GPU: RTX 20 / 30](https://img.shields.io/badge/GPU-RTX_20_%2F_30-5b713b?style=flat-square)](#will-it-work-with-my-setup)
[![License: MIT](https://img.shields.io/badge/license-MIT-334234?style=flat-square)](LICENSE)
[![upstream-check](https://github.com/ztwzeroo/DLSS5-FrameGen/actions/workflows/upstream-check.yml/badge.svg)](https://github.com/ztwzeroo/DLSS5-FrameGen/actions/workflows/upstream-check.yml)

> **Developer preview.** Best suited to contributors and experienced modders using disposable test copies. The file-safety, rollback and checksum issues from the [2026-09-20 review](docs/reviews/2026-09-20-project-review.md) are fixed and pinned by regression tests (the review's repro script now reports all nine behaviors fixed). No verified in-game benchmarks yet. **Read the [current limitations](docs/STATUS.md) before installing.**

**Have an RTX 20/30 and a single-player D3D12 game with native frame-generation support?** We are looking for early testers. See the [recommended test games](docs/TEST-GAMES.md), [download the Windows developer preview](../../releases/latest), try it on a backed-up test copy, and [share a success or failure report](https://github.com/ztwzeroo/DLSS5-FrameGen/issues/new?template=game-test.yml). We have not yet verified the combined setup in a real Windows game; your report helps establish which configurations actually work.

<p>
  <a href="../../releases"><img src="https://img.shields.io/badge/Download-Releases_(exe_/_linux)-d3ff6a?style=for-the-badge&amp;labelColor=263021" alt="Download from Releases"></a>
  <a href="#get-started"><img src="https://img.shields.io/badge/Read-setup_guide-354a30?style=for-the-badge&amp;labelColor=263021" alt="Read setup guide"></a>
  <a href="https://github.com/ztwzeroo/DLSS5-FrameGen/issues/new?template=game-test.yml"><img src="https://img.shields.io/badge/Share-a_game_test-354a30?style=for-the-badge&amp;labelColor=263021" alt="Share a game test"></a>
</p>

[Compatibility](#will-it-work-with-my-setup) · [FAQ](#frequently-asked-questions) · [Known issues](docs/STATUS.md) · [Contribute](CONTRIBUTING.md) · [Changelog](CHANGELOG.md) · [Dev log](docs/devlog/2026-09-20.md)

*Prebuilt Windows EXE and Linux binaries ship on the [Releases](../../releases) page — or run from source with Python 3.10+. No upstream DLLs are bundled; components are fetched and checksum-verified at install time. See [Downloads & manual placement](DOWNLOADS.md).*

## Why this project?

Setting up two graphics mods means managing two layers of files, configuration and troubleshooting. This project brings the coordination into one small, open-source CLI.

| You want to… | This toolkit helps you… |
|---|---|
| Try both layers together | Download the upstream components into one local kit. |
| Configure frame generation | Choose a runtime, multiplier ceiling and optimization tier. |
| Understand your installation | Record installed files and inspect backend logs. |
| Help others with the same GPU | Share reproducible game tests using a structured report. |

The image layer is still configured in **DLSS5-Swapper's own interface**. Rendering and frame generation are provided by the upstream projects; this repository provides the workflow around them.

## The workflow at a glance

```mermaid
flowchart LR
    A["01 · FETCH<br/>Components"] --> B["02 · CONFIGURE<br/>Image layer"]
    B --> C["03 · INSTALL<br/>Frame generation"]
    C --> D["04 · TEST<br/>Game + logs"]
    classDef step fill:#172118,color:#eef4e5,stroke:#718e53,stroke-width:1px
    class A,B,C,D step
```

*Setup workflow only. This diagram is not a gameplay demonstration or performance result.*

<p align="center"><img src="assets/demo.svg" alt="dlss-combo workflow demo" width="640"></p>

*Animated CLI walkthrough: `fetch` → `install` → `doctor` → `report`. Illustrative output, not measured game results.*

## Will it work with my setup?

These are the **target requirements**, not a verified compatibility list.

| Component | Target |
|---|---|
| GPU | NVIDIA RTX 20 series or RTX 30 series |
| OS | Windows 10/11, 64-bit |
| Game | D3D12, with native DLSS Frame Generation support |
| Driver | Follow the upstream requirements; this CLI warns below R580 |
| Python | 3.10 or later |
| Use | Single-player test copies, without anti-cheat |

RTX 40/50, Vulkan games and games without native frame-generation support are outside this project's current target. Other mods may conflict. **Do not use this with anti-cheat or competitive multiplayer games.**

**Multiple NVIDIA GPUs:** when several cards are present, the tool picks the **first card with a supported architecture** (RTX 20/30) and `doctor` lists every card in the rig so you can confirm which one was selected; `install DIR --arch sm75|sm86` overrides the choice. Looking for a suitable game? See [Recommended test games](docs/TEST-GAMES.md).

## Get started

Use an independently backed-up or disposable game copy. Uninstall validates its manifest, skips externally modified files and restores pre-existing user configs — but no restore is a substitute for a backup. See the [known issues](docs/STATUS.md#known-issues).

### 1. Get the toolkit

**Easiest (no Python needed):** grab `dlss-combo-<version>-windows-x64.zip` from the [Latest release](../../releases/latest), extract `dlss-combo.exe`, and use it anywhere below in place of `py -m dlss_combo`:

```powershell
.\dlss-combo.exe fetch
.\dlss-combo.exe install "C:/Games/TestCopy/Binaries/Win64"
```

**From source:** [download the source ZIP](https://github.com/ztwzeroo/DLSS5-FrameGen/archive/refs/heads/main.zip), extract it, and open PowerShell in the extracted folder. Then run:

```powershell
py -m pip install .
py -m dlss_combo fetch
```

Prefer Git? Clone `https://github.com/ztwzeroo/DLSS5-FrameGen.git`, open that folder, and run the same commands. The Python package and CLI retain the original names `dlss_combo` and `dlss-combo`.

Add `--check-update` to any command (for example `py -m dlss_combo --check-update doctor DIR`) for a non-blocking check that a newer dlss-combo release exists — it prints one line and never interrupts the run, and it is skipped silently when offline.

### 2. Configure the image layer

Open the downloaded **DLSS5-Swapper portable EXE** in `~/dlss-combo-kit/swapper/`. Use its interface and upstream instructions to configure your **test copy** of the game. If the asset is a ZIP, follow the upstream extraction instructions first.

### 3. Add frame generation

Replace the example path with the folder containing your test game's **actual rendering EXE**:

```powershell
py -m dlss_combo install "C:/Games/TestCopy/Binaries/Win64" --mfg 4x
```

`4x` is a ceiling, not a promise of four times the measured FPS. The game and runtime determine what is supported. Start by checking your base frame rate before increasing the multiplier.

### 4. Play, inspect, share

Enable frame generation in the game's graphics settings if available. After a test session:

```powershell
py -m dlss_combo doctor "C:/Games/TestCopy/Binaries/Win64"
```

A successful file installation or detected ReShade folder does **not** prove either rendering layer is active. Diagnostics have known limitations; [report your observed result](https://github.com/ztwzeroo/DLSS5-FrameGen/issues/new?template=game-test.yml), including failures. To make that easy, `report` generates a paste-ready offline game-test report:

```powershell
py -m dlss_combo report "C:/Games/TestCopy/Binaries/Win64"
```

<details>
<summary><strong>More commands and tuning options</strong></summary>

Use `py -m dlss_combo --help` or `py -m dlss_combo install --help` for the full CLI.

| Option / command | What it does |
|---|---|
| `fetch --runtime 310.9` | Download the 310.9 runtime kit; 310.1 is also available. |
| `fetch --kit-dir PATH` | Use a custom component cache. Use the same path with `install`. |
| `fetch --refresh` | Redownload components. Per-file atomic staging; other components' metadata is preserved. |
| `install DIR --tier 0` | Choose the upstream stock-numerics tier; tiers 0–3 are exposed. |
| `install DIR --mfg 2x` | Set a lower frame-generation ceiling. 3x, 4x and 6x are also exposed. |
| `install DIR --arch sm86` | Override the GPU-architecture check; driver checks still run. |
| `install DIR --proxy winmm.dll` | Pin a specific proxy DLL name (default order follows the upstream tool-class proxies first). |
| `install DIR --launch-swapper` | Launch the downloaded DLSS5-Swapper portable after installing (checksum-verified). |
| `report DIR` | Print a paste-ready markdown game-test report (offline, read-only). Add `--out FILE` to save it. |
| `--check-update` (before any command) | Non-blocking check for a newer dlss-combo release; skipped when offline. |
| `uninstall DIR` | Remove managed files. Read the file-safety and restoration issues first. |

6X requires a compatible 310.9 build **and** game. Setting 6X with 310.1 does not make that runtime support it. Some optimization tiers are also runtime-dependent. Consult the [upstream INI](https://github.com/sdli1995/dlssg_for_sm86/blob/main/dlssg_sm86.ini) for meanings and constraints.

</details>

## Linux / Steam Proton

Windows games running through Proton are still Windows processes, so the frame-generation layer is expected to apply the same way — **not yet verified end-to-end by this project on Linux**. Grab `dlss-combo-<version>-linux-x64.zip`, then point the CLI at the folder containing the game's **rendering EXE**. The reliable way to find it is Steam → *Manage* → **Browse local files** (Proton installs often live under the prefix's `drive_c`, but the layout is not guaranteed — the Browse-local-files location is the reliable reference):

```bash
chmod +x dlss-combo
./dlss-combo install "/path/to/Game/Binaries/Win64"
```

Some setups add Steam launch options so Wine loads the proxy and Proton exposes
NVAPI/CUDA:

```
WINEDLLOVERRIDES="version=n,b" PROTON_ENABLE_NVAPI=1 PROTON_NVIDIA_NVCUDA=1 %command%
```

> These options are community convention (the route [DLSS Unlocked](https://github.com/ShyVortex/DLSS-Unlocked) documents), **not verified with this toolkit** — check your Proton version's behavior against [Valve's config notes](https://github.com/ValveSoftware/Proton#runtime-config-options) before relying on them. Substitute the actual proxy name (`winmm`/`dbghelp`/…) if it is not `version.dll`.

- The image layer (DLSS5-Swapper) is a Windows GUI app; running it via Wine is upstream-experimental — on Linux, validate the frame-generation layer first.
- **Linux binaries require glibc >= 2.35** — the real floor is measured per build by extracting the embedded ELF libraries from the PyInstaller archive (an outer-file string scan under-reports it; the current build's floor is in each zip's `build-info.txt`). Other distros are unverified; to target older systems, run from source.

## What has actually been tested?

| Evidence | Current state |
|---|---|
| Offline Python tests | 155 passing at v0.2.0; CI runs the suite on Windows/Linux/macOS on every push |
| Review regression | The 2026-09-20 repro script reports all nine fixed behaviors |
| Release binaries | Windows EXE + Linux x64 built by GitHub Actions from each tagged commit |
| Windows game sessions | Not yet validated by this project |
| FPS, latency and image quality | No verified measurements published |
| File safety | Review issues fixed in code with regression coverage; in-game safety still unverified |

We welcome negative results as well as successful runs. A useful comparison uses the **same scene and settings** for the original game, image layer only, frame generation only, and both layers together. Do not infer real FPS gains from the configured multiplier.

**[Submit a game test →](https://github.com/ztwzeroo/DLSS5-FrameGen/issues/new?template=game-test.yml)** · [Report a bug](https://github.com/ztwzeroo/DLSS5-FrameGen/issues/new?template=bug-report.yml) · [Contribute code](CONTRIBUTING.md)

## Frequently asked questions

<details>
<summary><strong>Is there a Windows EXE? Is it a GUI?</strong></summary>

Yes — [Releases](../../releases/latest) carries a prebuilt `dlss-combo.exe` (Windows x64) and a Linux x64 binary, built by GitHub Actions from the tagged commit. This is a command-line tool, not a graphical installer. The binaries are unsigned, so SmartScreen may show a reputation prompt. The upstream Swapper portable EXE is a separate application.

</details>

<details>
<summary><strong>Does this replace DLSS5-Swapper or implement DLSS 5?</strong></summary>

No. DLSS5-Swapper manages the image-layer routes, and dlssg_for_sm86 provides frame generation. This toolkit coordinates their setup and diagnostics. It is an independent community project.

</details>

<details>
<summary><strong>Will it double my FPS or work in every game?</strong></summary>

There are no verified performance results for this combined toolkit yet. GPU, game, runtime, base frame rate and other mods all matter. Configured multipliers are not measured FPS gains.

</details>

<details>
<summary><strong>What language is the CLI output in?</strong></summary>

Since v0.2.0 the CLI is English-only — help text, diagnostics and errors (internal source comments remain Chinese). If you see output from an older release that mixes languages, include the original output when reporting a problem, or update to the latest release.

</details>

<details>
<summary><strong>Where are the gameplay screenshots and benchmarks?</strong></summary>

We will add them when reproducible Windows/NVIDIA tests are available. The banner and workflow diagram are explanatory graphics, not evidence of in-game results. Real game reports, including unsuccessful tests, are welcome.

</details>

## Where we're headed

- [x] Add regression protection for externally modified files and original configuration recovery.
- [x] Re-verify cached files and keep the previous kit usable if refresh fails.
- [x] Make the CLI English-only (help, diagnostics, errors), guarded by a regression test.
- [ ] Add an installation preview and improve per-session diagnostics with real game evidence.
- [ ] Validate Windows behavior and publish reproducible RTX 20/30 game results.

See the [English status and known issues](docs/STATUS.md), [detailed audit (Chinese)](docs/reviews/2026-09-20-project-review.md), and [contributor guide](CONTRIBUTING.md).

## Built on the work of

**[DLSS5-Swapper](https://github.com/rakanki911/DLSS5-Swapper)** — image-layer installation routes and component management.
**[dlssg_for_sm86](https://github.com/sdli1995/dlssg_for_sm86)** — the DLSS-G proxy and frame-generation implementation.

Please support the upstream maintainers. This repository does not modify, rebuild or redistribute their binaries; `fetch` downloads components from upstream. Self-recorded hashes check local integrity but do not authenticate upstream assets unless upstream checksums are available.

[MIT licensed](LICENSE). Independent community project, not affiliated with or endorsed by NVIDIA or either upstream project. DLSS and RTX are NVIDIA trademarks.
