# Recommended games for testing frame generation on RTX 20/30

A good test target has three properties: **native DLSS Frame Generation support** (the game itself exposes a Frame Generation option, so the proxy has a real hook to unlock), **D3D12** as the rendering API, and **single-player design without kernel-level anti-cheat** (never test frame-generation injection against anti-cheat or competitive multiplayer). Every support claim below is *reported* support — verify the option exists in your own game copy before drawing conclusions. Before enabling 4X, measure your **base frame rate without frame generation and aim for at least 55–60 FPS**: frame generation multiplies what the game already delivers and degrades badly from a low base.

| Game | Cost | Why it's a good test | Native-FG evidence |
|---|---|---|---|
| The Sinking City 2 | Free demo (Steam) | The demo exposes ONLY the DLSS Frame Generation option and gates it to RTX 40+ — exactly the unlock scenario dlssg_for_sm86 targets. A zero-cost first test. | [Steam demo store page](https://store.steampowered.com/app/3566310/The_Sinking_City_2/) + Steam Community discussion (June 2026) confirming FG-only, RTX 40-gated |
| Cyberpunk 2077 | Frequent deep sales | Native DLSS FG plus a built-in benchmark for objective before/after numbers. | [NVIDIA RTX games list](https://www.nvidia.com/en-us/geforce/news/nvidia-rtx-games-engines-apps) |
| Black Myth: Wukong | Paid | Native DLSS FG, D3D12, single-player. | [NVIDIA RTX games list](https://www.nvidia.com/en-us/geforce/news/nvidia-rtx-games-engines-apps) |
| Alan Wake 2 | Paid | Native DLSS FG. | [NVIDIA RTX games list](https://www.nvidia.com/en-us/geforce/news/nvidia-rtx-games-engines-apps) |
| The Witcher 3 (patch 4.04+) | Often heavily discounted | FG added in a post-launch patch. | [PCGamingWiki upscaling list](https://www.pcgamingwiki.com/wiki/List_of_games_that_support_high-fidelity_upscaling) |
| Avatar: Frontiers of Pandora | Paid | Native DLSS FG. | [NVIDIA RTX games list](https://www.nvidia.com/en-us/geforce/news/nvidia-rtx-games-engines-apps) |

Reference lists used to compile the evidence column: the [NVIDIA RTX games list](https://www.nvidia.com/en-us/geforce/news/nvidia-rtx-games-engines-apps) and the [PCGamingWiki list of games that support high-fidelity upscaling](https://www.pcgamingwiki.com/wiki/List_of_games_that_support_high-fidelity_upscaling).

**Reporting results:** run `dlss-combo report <game-dir>` to print a paste-ready game-test report, and share it via the [game-test issue template](https://github.com/ztwzeroo/DLSS5-FrameGen/issues/new?template=game-test.yml) — unsuccessful tests are just as valuable as successful ones.
