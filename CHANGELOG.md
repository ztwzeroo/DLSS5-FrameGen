# Changelog

All notable changes to this project are documented here. The format follows
[Keep a Changelog](https://keepachangelog.com/en/1.1.0/); versioning is
[SemVer](https://semver.org/) with a `0.x` experimental prefix. Evidence links
point to files in this repository (`docs/`) so the trail is auditable offline.

## [0.1.1] — 2026-09-20

### Fixed

- **Preserve user-modified `dlssg_sm86.ini` across reinstall and uninstall**
  (release-acceptance review P1). Reinstall now keeps an externally modified
  INI instead of overwriting it after warning (the manifest records an
  `ini_user_managed` flag that persists across upgrades); uninstall no longer
  overwrites an in-place user file with the pre-existing backup — the original
  config is saved beside it as `dlssg_sm86.ini.pre-existing`.
  Regression tests: `tests/test_review3.py`.
- Single-source package version (`pyproject.toml` now reads
  `dlss_combo.__version__`); `--version` previously could disagree with the
  built artifact.

### Changed

- **Release process gate**: the release workflow now runs the offline test
  suite **and** the review repro audit **and** a functional smoke test of the
  *packaged binary* (install → doctor → uninstall against a fabricated kit),
  on both Windows and Linux — no longer a `--version`-only check.
- **Linux binary glibc floor**: built on `ubuntu-22.04` (was `ubuntu-latest`);
  the whole-binary GLIBC symbol floor is measured per build and ships in the
  zip's `build-info.txt` (v0.1.1 measured **GLIBC_2.14**, down from 2.38 in
  v0.1.0). Other distros remain unverified; glibc >= 2.17 is the conservative
  recommendation.
- **Release page**: marked **pre-release** (matches the developer-preview
  stage); notes are English-first with Windows as the main download and Linux
  labelled experimental; each zip now contains `QUICKSTART.txt`, `LICENSE`
  and `build-info.txt` (source commit, build time, measured glibc floor).
- **Linux/Proton guidance** (README + release notes): locate the game via
  Steam → *Browse local files* instead of assuming a fixed prefix layout;
  `WINEDLLOVERRIDES`/`PROTON_*` launch options are labelled community
  convention, not verified with this toolkit, with a pointer to Valve's
  Proton config docs.
- Unsigned-binary wording is neutral: verify SHA256, decide about security
  warnings yourself; no instruction to bypass protections.

## [0.1.0] — 2026-09-20

### Added

- Initial public toolkit: `fetch` / `install` / `uninstall` / `doctor` CLI
  coordinating [DLSS5-Swapper](https://github.com/rakanki911/DLSS5-Swapper)
  (DLSS 5 image layer) with
  [dlssg_for_sm86](https://github.com/sdli1995/dlssg_for_sm86) (frame
  generation on RTX 20/30); SHA256-verified kit downloads pinned to an
  upstream commit; manifest-driven install/rollback/uninstall; bilingual docs.
- First release binaries for Windows x64 and Linux x64 via GitHub Actions.

### Security / file-safety (from the 2026-09-20 project review, all fixed here)

- Manifest validation before any destructive step: known schema version,
  allow-listed filenames only, relative paths, no `..`/absolute/symlink
  escapes, backups confined to `.dlss-combo/` (review A).
- Hash-based ownership: files whose current hash no longer matches the install
  record are treated as third-party and never touched (review B).
- Pre-existing user INI backed up (`pre-existing`, distinct from tool-history
  backups) and restored on uninstall (review C).
- Every required kit file must carry a well-formed matching SHA256; cache hits
  re-verify with automatic refetch; Swapper binary hash-checked before launch
  and refused if a ZIP (review D, J).
- Atomic disk writes everywhere (temp file + replace), rollback restores
  deleted files and cleans partial temp files (review E).
- Kit fetch is transactional per file; per-runtime commit records; Swapper
  metadata survives refreshes (review F).
- Doctor accuracy: newest-log/newest-event route parsing, strict booleans,
  empty ReShade folders no longer reported as an installed image layer,
  non-zero exit on detected problems (review G).
- Proxy order follows the upstream tool-class recommendation
  (`version → winmm → dbghelp → dinput8` before the riskier `d3d12`/`dxgi`),
  `--proxy` pins a name explicitly (review H).
- `--arch` no longer skips driver checks; `310.1 + 6x` rejected per upstream
  limits (review I).

The nine reproduced problem behaviors are pinned by
`docs/reviews/2026-09-20-repro.py` (all report fixed) and migrated into
regression tests (`tests/test_review2.py`).

[0.1.1]: https://github.com/ztwzeroo/DLSS5-FrameGen/releases/tag/v0.1.1
[0.1.0]: https://github.com/ztwzeroo/DLSS5-FrameGen/releases/tag/v0.1.0
