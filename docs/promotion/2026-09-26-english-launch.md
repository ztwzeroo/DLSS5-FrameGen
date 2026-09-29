# English launch kit — DLSS5-FrameGen

Prepared on 2026-09-26 for the public v0.1.3 developer preview. Confirm each community's current rules before posting. Draft copy appears above; publication attempts and their actual outcomes are recorded in the table below. Do not claim game compatibility or FPS gains until a reproducible test exists.

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
| Guru3D | 2026-09-29 | https://forums.guru3d.com/threads/dlss5-framegen-rtx-20-30-dlss-5-frame-generation-setup-tool-testers-wanted.461994/ | Published in Game Tweaks and Modifications with a [conceptual workflow graphic](assets/guru3d-workflow.png); asks for RTX 20/30 game-test reports and makes no verified performance claim. |
| r/DLSS | 2026-09-29 | https://www.reddit.com/r/DLSS/comments/1wt575d/rtx_2030_dlss_5_frame_generation_i_built_an/ | Published by u/Livid-Election-2049 with the DLSS 5 flair and the conceptual workflow graphic. The post asks for reproducible RTX 20/30 reports and states that no combined in-game result or FPS gain has been verified. [Publication screenshot](assets/reddit-dlss-post-proof.png). |
| r/ReShade | 2026-09-29 | https://www.reddit.com/r/ReShade/comments/1wt5dfm/reshade_opens_but_is_the_dlss_5_mod_actually/ | Published by u/Livid-Election-2049 as an image post with a [conceptual test matrix](assets/reshade-test-matrix.png). It asks how to confirm that an image effect is active and requests reproducible game reports; the image and text explicitly say results are unknown. [Publication screenshot](assets/reddit-reshade-post-proof.jpg). |
| r/OptimizedGaming | 2026-09-29 | https://www.reddit.com/r/OptimizedGaming/comments/1wt5jxw/rtx_2030_dlss_5_mod_frame_generation_a_fourstate/ | Submitted a distinct [four-state test-protocol graphic](assets/optimizedgaming-test-protocol.png), but AutoModerator removed the post as a technical-support question. It is **not a public publication**. [Removal screenshot](assets/reddit-optimizedgaming-removed.jpg). Do not repost to evade the filter. |
| r/losslessscaling | 2026-09-29 | https://www.reddit.com/r/losslessscaling/comments/1wt5nhc/lsfg_vs_gameintegrated_dlss_fg_on_rtx_2030_two/ | Published by u/Livid-Election-2049 with the Discussion flair and an original [two-path frame-generation diagram](assets/losslessscaling-fg-paths.png). The post explains that this project does not modify Lossless Scaling and asks for controlled LSFG-versus-game-integrated-FG comparisons without claiming results. The full post and image were also verified in a logged-out browser. [Publication screenshot](assets/reddit-losslessscaling-post-proof.jpg). |

For every channel, track visits to the canonical release, completed downloads, distinct usable test reports, and confirmed game configurations. GitHub stars alone are a weak success measure for a tool that has not yet been validated in games.
