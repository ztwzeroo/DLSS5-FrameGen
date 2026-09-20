# Contributing

Thanks for helping make DLSS5-FrameGen useful and dependable for RTX 20/30 owners.

Read the [preview limitations](docs/STATUS.md) first. The immediate priority is safe file handling and reliable verification. Real Windows testing is valuable, but use disposable test directories or independently backed-up game copies.

## Report a game test

Use the [game-test form](https://github.com/ztwzeroo/DLSS5-FrameGen/issues/new?template=game-test.yml). Include the game/build, GPU, driver, OS, upstream versions, runtime, proxy and settings. Explain whether you verified file installation, proxy loading, frame generation or the image layer.

Only report FPS and latency numbers you measured. Use the same scene and settings for all comparisons, and include your measurement method. An unsupported game or a failed attempt is still a useful result. Do not post account details, secrets or personal paths in logs.

## Report a bug

Use the [bug form](https://github.com/ztwzeroo/DLSS5-FrameGen/issues/new?template=bug-report.yml). Provide the exact command, expected behavior, actual behavior and a minimal reproduction using fake files where possible. Link an existing report if it describes the same issue.

## Develop locally

On Windows, in the repository root:

```powershell
py -m venv .venv
.venv\Scripts\python -m pip install -e . pytest
.venv\Scripts\python -m pytest -q
```

On macOS or Linux, use `python3 -m venv .venv` and `.venv/bin/python`. Offline test success does not validate Windows filesystem behavior or GPU compatibility.

Keep changes focused. For file operations, test externally replaced files, original INI preservation, out-of-directory paths and partial-write failures. Use temporary directories and fake binaries; tests must never modify real game installations. Update fixture hashes when intentionally simulating a legitimate new kit.

For a pull request, explain the problem, resulting behavior, verification and remaining limits. Do not weaken safety assertions to make tests pass. Keep real-game evidence separate from unit-test evidence.

## Scope

The rendering implementations belong to the upstream projects. This repository coordinates component downloads, frame-generation configuration and diagnostics. Avoid adding upstream binary files, claiming unmeasured FPS improvements, or presenting a file-presence check as proof of in-game activation.
