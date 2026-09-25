# English launch kit — DLSS5-FrameGen

Prepared on 2026-09-26 for the public v0.1.3 developer preview. Confirm each community's current rules before posting. These are drafts, not records of publication. Do not claim game compatibility or FPS gains until a reproducible test exists.

## Positioning

**One sentence:** An open-source command-line toolkit that coordinates DLSS5-Swapper's image layer with dlssg_for_sm86 frame generation for RTX 20/30 test setups.

**What it does:** Fetches upstream components, configures the frame-generation proxy, records managed files, supports uninstall, and reads diagnostic logs. The image layer is configured in DLSS5-Swapper's own app.

**What it does not establish:** A successful install or green offline test does not establish that both layers work in a particular game, nor does a configured 4X/6X ceiling equal measured FPS.

**Primary audience:** Experienced Windows 10/11 RTX 20/30 owners who can test a backed-up single-player D3D12 game with native DLSS Frame Generation support. Linux/Proton is experimental and should be recruited separately after environment-specific testing.

**Canonical links:** [Project](https://github.com/ztwzeroo/DLSS5-FrameGen) · [Windows download](https://github.com/ztwzeroo/DLSS5-FrameGen/releases/latest) · [Known limitations](https://github.com/ztwzeroo/DLSS5-FrameGen/blob/main/docs/STATUS.md) · [Game-test form](https://github.com/ztwzeroo/DLSS5-FrameGen/issues/new?template=game-test.yml)

## Guru3D forum: first public tester post

Suggested destination: a relevant NVIDIA GeForce / graphics utilities discussion, after reading that board's current posting rules. Do not cross-post the same text to multiple boards.

**Title:** DLSS5-FrameGen: open-source RTX 20/30 setup toolkit — looking for real game testers

> Hi everyone. I made [DLSS5-FrameGen](https://github.com/ztwzeroo/DLSS5-FrameGen), an open-source command-line toolkit for people experimenting with DLSS 5 image processing and frame generation on RTX 20/30 hardware.
>
> It coordinates two existing community projects: [DLSS5-Swapper](https://github.com/rakanki911/DLSS5-Swapper) for the image layer, and [dlssg_for_sm86](https://github.com/sdli1995/dlssg_for_sm86) for frame generation. My tool downloads the upstream components when requested, configures the frame-generation proxy, tracks the files it installs, and helps inspect logs. It does not implement either rendering layer or bundle the upstream DLLs.
>
> The [Windows x64 developer preview](https://github.com/ztwzeroo/DLSS5-FrameGen/releases/latest) is a command-line EXE, not a GUI installer. It is unsigned. The source, build workflow, [limitations](https://github.com/ztwzeroo/DLSS5-FrameGen/blob/main/docs/STATUS.md), and checksum file are public. Offline tests and packaged-binary checks pass, but I have **not yet verified the combined setup in a real Windows game** and have no measured FPS or image-quality claim.
>
> I am looking for careful tests on RTX 20/30 cards with single-player D3D12 games that already support native DLSS Frame Generation. Please use a backed-up test copy and avoid anti-cheat multiplayer games. Successes, crashes, failed installs, and cases where only one layer activates are all useful. The [test form](https://github.com/ztwzeroo/DLSS5-FrameGen/issues/new?template=game-test.yml) asks for the game build, GPU, driver, settings, and evidence.
>
> If you have tried a similar combination, which game and GPU should we validate first? I will keep a public compatibility table based on reproducible reports.

## Short post for a community that permits self-promotion

**Title:** Looking for RTX 20/30 testers for an open-source DLSS 5 + frame-generation setup tool

> I built [DLSS5-FrameGen](https://github.com/ztwzeroo/DLSS5-FrameGen), a Windows command-line toolkit that coordinates DLSS5-Swapper with dlssg_for_sm86. It fetches upstream components, configures the frame-generation proxy, tracks installed files and reads diagnostic logs. The [v0.1.3 developer preview](https://github.com/ztwzeroo/DLSS5-FrameGen/releases/latest) has a prebuilt unsigned EXE. I have no verified in-game results yet, so I am collecting both success and failure reports from RTX 20/30 owners using backed-up single-player test copies. [Known limitations](https://github.com/ztwzeroo/DLSS5-FrameGen/blob/main/docs/STATUS.md) · [Game-test form](https://github.com/ztwzeroo/DLSS5-FrameGen/issues/new?template=game-test.yml).

Do not use this in r/nvidia without moderator approval: its published rules prohibit self-advertising. The short post is for communities whose current rules allow a developer announcement.

## Publishing sequence and evidence

1. Confirm the GitHub download points to the intended version, the release text is accurate, and the test form works.
2. Publish one Guru3D tester invitation. Respond to technical questions and record the post URL and date here.
3. After at least one independent Windows RTX game report with logs and reproducible steps, update a public compatibility table that includes failures and unknowns.
4. Share measured outcomes in other communities only when their rules permit it. Use a new post tailored to each audience, not a link dump.

| Channel | Publication date | URL | Status / learning |
|---|---|---|---|
| Guru3D | — | — | Draft prepared; not posted |
| Other community | — | — | Not posted |

For every channel, track visits to the canonical release, completed downloads, distinct usable test reports, and confirmed game configurations. GitHub stars alone are a weak success measure for a tool that has not yet been validated in games.
