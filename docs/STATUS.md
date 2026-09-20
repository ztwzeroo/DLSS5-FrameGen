# Preview status & known issues

[← Back to the project](../README.md)

**This is an experimental source preview, not a stable installer.** It is intended for contributors and experienced modders working on disposable directories or independently backed-up game copies.

This page describes the published preview based on code commit `9e55ebb`. Uncommitted local fixes are not part of this release. Check the published source and evidence before assuming a problem has been fixed.

## Evidence so far

- 81 offline Python tests pass on macOS. They use simulated GPUs, downloaded bytes and game directories.
- A Python wheel builds, and an isolated CLI version check succeeds.
- Nine known problem behaviors were reproduced with temporary fake files.
- No Windows/NVIDIA game session, image-quality comparison, latency test or FPS benchmark has been validated by this project.

Upstream support claims and configuration limits are not a substitute for testing the combined setup. A `4x` or `6x` setting is a frame-generation ceiling, not a measured performance improvement.

## Known issues

### File deletion and ownership

Uninstall trusts paths from the installation manifest. An edited or malformed manifest can point outside the game directory. Reinstall and uninstall also identify managed files by name without adequately checking whether another mod replaced them.

**Impact:** unrelated or externally modified files can be removed or overwritten. Do not import or modify manifests. Use disposable copies until bounded paths and ownership validation are implemented.

### Original configuration and recovery

An existing `dlssg_sm86.ini` can be overwritten without a restorable original backup. A copy that writes partial data and then fails can leave a corrupt DLL instead of restoring the previous one. Manifest writes are not atomic.

**Impact:** uninstall is not a guaranteed return to the original state. Keep a separate backup; do not use this tool as the sole backup or recovery mechanism.

### Download and launch validation

Missing entries in the checksum map can pass verification. Cached Swapper files are not rechecked before launch. Locally computed hashes establish a baseline but do not independently authenticate an upstream binary.

**Impact:** the preview does not deliver complete checksum enforcement. Review upstream download verification instructions and avoid modified/shared component caches.

### Cache refresh and component records

Interrupted refresh can leave mixed files. Refreshing the frame-generation kit drops Swapper metadata, and different runtimes share one commit field. A cache hit checks existence instead of repairing corrupted content.

### Diagnostics

The log parser can select an earlier successful event rather than a later failure, or reuse historical evidence. ReShade/RenoDX/Feeder markers can overstate the presence of a working DLSS 5 layer. Diagnostic failures do not consistently produce a failing CLI exit code.

**Interpretation:** distinguish files present, proxy loaded, frame-generation route active, and a visually verified image layer. None of these alone establishes measured performance gains.

### Compatibility and asset handling

A free proxy filename does not mean the game loads it. The d3d12 fallback order needs review. GPU override bypasses driver detection, only the first GPU is considered, and runtime/setting combinations are not fully validated. A portable ZIP cannot be treated as a launched EXE.

The project targets Windows 10/11 x64, RTX 20/30, and D3D12 games with native DLSS Frame Generation. Compatibility of the combined setup remains unverified. Use only single-player test copies without anti-cheat.

## How to help

Prioritize bounded filesystem operations, ownership checks, original-file restoration, strict checksums, and failure recovery. Regression tests should assert that unrelated files remain byte-for-byte unchanged.

The [detailed audit (Chinese)](reviews/2026-09-20-project-review.md) includes file locations, reproduction results and acceptance criteria. The [reproduction script](reviews/2026-09-20-repro.py) uses temporary files and does not launch real binaries. **Its successful completion means the known bugs are reproducible, not that the tool is safe.**

For real game reports, use the [game-test form](https://github.com/ztwzeroo/DLSS5-FrameGen/issues/new?template=game-test.yml). Include unsuccessful attempts and clearly label what you did and did not measure.
