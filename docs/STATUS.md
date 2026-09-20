# Preview status & known issues

[← Back to the project](../README.md)

**This is an experimental source preview, not a stable installer.** It is intended for contributors and experienced modders working on disposable directories or independently backed-up game copies.

This page describes the tree after the 2026-09-20 review fixes landed (see [the review](2026-09-20-project-review.md) and [repro script](2026-09-20-repro.py); all nine reproduced behaviors now assert fixed). In-game behavior remains unverified.

## Evidence so far

- 107 offline Python tests pass; CI runs them on Windows/Linux/macOS on every push.
- A Python wheel builds, and an isolated CLI version check succeeds.
- The nine reproduced problem behaviors from the 2026-09-20 review are fixed and covered by regression tests; the repro script reports all nine as fixed.
- No Windows/NVIDIA game session, image-quality comparison, latency test or FPS benchmark has been validated by this project.

Upstream support claims and configuration limits are not a substitute for testing the combined setup. A `4x` or `6x` setting is a frame-generation ceiling, not a measured performance improvement.

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
