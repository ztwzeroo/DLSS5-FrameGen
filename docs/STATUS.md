# Preview status & known issues

[← Back to the project](../README.md)

**This is an experimental source preview, not a stable installer.** It is intended for contributors and experienced modders working on disposable directories or independently backed-up game copies.

This page describes the tree after the 2026-09-20 review fixes landed (see [the review](reviews/2026-09-20-project-review.md) and [repro script](reviews/2026-09-20-repro.py), plus the [v0.1.1 independent review](reviews/2026-09-20-v0.1.1-independent-review.md) and its [repro](reviews/2026-09-20-v0.1.1-independent-repro.py) — all seventeen reproduced behaviors now assert fixed), updated for the 2026-09-29 v0.2.0 hardening (doctor session semantics, proxy-order lock, English CLI, multi-GPU selection). In-game behavior remains unverified.

## Evidence so far

- 155 offline Python tests pass; CI runs them on Windows/Linux/macOS on every push.
- A Python wheel builds, and an isolated CLI version check succeeds.
- The nine reproduced problem behaviors from the 2026-09-20 review are fixed and covered by regression tests; the repro script reports all nine as fixed.
- No Windows/NVIDIA game session, image-quality comparison, latency test or FPS benchmark has been validated by this project.

Upstream support claims and configuration limits are not a substitute for testing the combined setup. A `4x` or `6x` setting is a frame-generation ceiling, not a measured performance improvement.

## Fixed in v0.2.0 (2026-09-29)

- **Diagnostics semantics**: the session verdict is now the **last route event of the newest log** — a later failure is never hidden by an earlier success, and historical evidence is not reused as current. Unreadable route logs are reported as problems instead of crashing `doctor`, and image-layer files (ReShade/RenoDX/Feeder markers) are treated as **evidence only**, never as proof the DLSS 5 layer is active. Evidence: `tests/test_doctor_last_event.py`.
- **Proxy fallback order locked**: the candidate order — upstream tool-class proxies (`version → winmm → dbghelp → dinput8`) before the riskier `d3d12`/`dxgi` — is pinned by a regression test so it cannot silently change; `dxgi.dll` still requires an explicit opt-in. Evidence: `tests/test_proxy_order.py`.
- **CLI fully English**: help text, diagnostics and error messages are English-only, guarded by a regression test that scans user-facing strings for CJK characters. Internal source comments are unchanged. Evidence: `tests/test_english_cli.py`.

## Daily upstream-structure watch

The [upstream-check workflow](https://github.com/ztwzeroo/DLSS5-FrameGen/actions/workflows/upstream-check.yml) (`.github/workflows/upstream-check.yml`, driven by `scripts/upstream_check.py`) runs daily and checks the upstream *structure* dlss-combo depends on: the dlssg_for_sm86 main commit resolves, every kit file still exists at that commit, the generated INI keys are still accepted, and DLSS5-Swapper still publishes a selectable portable asset. Any drift (including failed fetches, e.g. rate limits) opens or updates an auto-labeled `upstream-check` issue, which closes itself once the check is green again. This watches structure, not authenticity — dlssg publishes no checksums.

## Fixed in v0.1.2 (independent v0.1.1 review, R1–R7)

First-install rollback now restores the user's original INI at every failure point (DLL/manifest/backup write); uninstall never overwrites any existing file or symlink when saving a restore copy (exclusive `O_CREAT|O_EXCL` with numbered fallbacks); temp files are random and exclusively created, and only paths registered by the current operation are cleaned; a missing or corrupted pre-existing backup aborts uninstall before any deletion; doctor treats the newest log as the diagnostic scope and labels older route events as historical; interrupted kit refreshes stage and switch atomically, leaving the previous kit usable. Evidence: `tests/test_review4.py` and the flipped independent repro script (all eight scenarios fixed). The glibc floor is now measured from the CArchive-extracted embedded ELF libraries (see the release workflow).

## Known issues

### File deletion and ownership — FIXED 2026-09-20

Manifests are now validated before any destructive step (schema version, allowed filenames only, relative paths, no `..`/absolute/symlink escapes, backups confined to `.dlss-combo/`), and files whose current hash no longer matches the install record are treated as third-party and left untouched.

**Evidence:** `tests/test_review2.py` traversal/absolute/backup-escape cases; review repro scenario 1 and 3 report fixed.

### Original configuration and recovery — FIXED 2026-09-20

Pre-existing user INI files are backed up as `pre-existing` (distinct from tool-history backups) and restored on uninstall across upgrades. All disk writes (DLL/INI/manifest/downloads) go through temp-file + atomic replace; rollback restores deleted files and cleans partial temp files.

**Evidence:** review repro scenarios 2 and 5 report fixed; `test_preexisting_ini_preserved_across_lifecycle`, `test_partial_copy_failure_leaves_old_dll_intact`.

### Download and launch validation — HARDENED 2026-09-20

Every required kit file must have a well-formed matching SHA256 (`missing checksum` is a failure), cache hits are re-verified with automatic refetch on corruption, and the Swapper binary is hash-checked (and refused if a ZIP) before launch. Self-computed hashes remain a local-integrity baseline, not upstream authentication — upstream publishes no checksums for these assets.

**Impact:** the preview does not deliver complete checksum enforcement. Review upstream download verification instructions and avoid modified/shared component caches.

### Cache refresh and component records

Interrupted refresh can leave mixed files. Refreshing the frame-generation kit drops Swapper metadata, and different runtimes share one commit field. A cache hit checks existence instead of repairing corrupted content.

### Diagnostics — FIXED 2026-09-29

The session verdict now follows the **last route event of the newest log** (a later failure is never hidden by an earlier success), unreadable route logs are reported as problems instead of crashing, and image-layer file markers are evidence only — never treated as layer activation. Detected problems exit non-zero. See "Fixed in v0.2.0" above; evidence: `tests/test_doctor_last_event.py`.

**Interpretation:** distinguish files present, proxy loaded, frame-generation route active, and a visually verified image layer. None of these alone establishes measured performance gains.

### Compatibility and asset handling

A free proxy filename does not mean the game loads it. The proxy fallback order is now locked and regression-tested (`tests/test_proxy_order.py`); `dxgi.dll` still requires an explicit opt-in. Multi-GPU rigs are enumerated — the **first supported-arch (RTX 20/30) card** is selected and `doctor` lists every card (`tests/test_gpu_multi.py`); `--arch` overrides the architecture choice but driver checks still run. Runtime/setting combinations are not fully validated. A portable ZIP cannot be treated as a launched EXE.

The project targets Windows 10/11 x64, RTX 20/30, and D3D12 games with native DLSS Frame Generation. Compatibility of the combined setup remains unverified. Use only single-player test copies without anti-cheat.

## How to help

Prioritize bounded filesystem operations, ownership checks, original-file restoration, strict checksums, and failure recovery. Regression tests should assert that unrelated files remain byte-for-byte unchanged.

The [detailed audit (Chinese)](reviews/2026-09-20-project-review.md) includes file locations, reproduction results and acceptance criteria. The [reproduction script](reviews/2026-09-20-repro.py) uses temporary files and does not launch real binaries. **Since v0.1.2 both scripts assert the FIXED behavior: successful completion means the reproduced defects no longer trigger — a specific regression guard, not proof that all file-safety concerns are resolved.**

For real game reports, use the [game-test form](https://github.com/ztwzeroo/DLSS5-FrameGen/issues/new?template=game-test.yml). Include unsuccessful attempts and clearly label what you did and did not measure.
