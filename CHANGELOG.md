# Changelog

All notable changes to this project are documented here. The format follows
[Keep a Changelog](https://keepachangelog.com/en/1.1.0/); versioning is
[SemVer](https://semver.org/) with a `0.x` experimental prefix. Evidence links
point to files in this repository (`docs/`) so the trail is auditable offline.

## [0.2.1] — 2026-09-29

### Added

- **Multi-source download fallback** — `fetch` now tries the official
  `raw.githubusercontent.com` URL first, then the equivalent `github.com` raw
  link, and only then community mirrors of the same URLs (default
  `gh-proxy.com`/`ghproxy.net`, overridable via `DLSS_COMBO_MIRRORS`). All
  failures list every source tried. We still never redistribute upstream files
  (`src/dlss_combo/fetch.py`, `tests/test_fetch_sources.py`).
- **`fetch --runtime all`** — one command downloads both DLSS-G runtimes
  (310.9 + 310.1) plus the Swapper portable (`src/dlss_combo/cli.py`,
  `tests/test_fetch_all.py`).
- **[DOWNLOADS.md](DOWNLOADS.md)** — manual download & placement guide on the
  repo page: direct upstream links for every file, why NVIDIA SDK terms forbid
  bundling them into our zips, mirror configuration, integrity notes.

## [0.2.0] — 2026-09-29

### Added

- Daily upstream-structure watch: the scheduled `upstream-check` workflow
  verifies the upstream shape this toolkit depends on (dlssg_for_sm86 main
  commit resolves, kit files still exist at that commit, generated INI keys
  stay accepted, DLSS5-Swapper still publishes a selectable portable asset)
  and opens/updates an auto-labeled issue on drift, closing it when green
  again. Evidence: `.github/workflows/upstream-check.yml`,
  `scripts/upstream_check.py`, selftest `tests/test_upstream_check.py`.
- `report` command: prints a paste-ready, offline, read-only game-test
  report (GPU landscape with the selected card, manifest summary, routing
  verdict, and an explicit "does NOT contain" section) for the game-test
  issue template. Evidence: `src/dlss_combo/report.py`, `tests/test_report.py`.
- `--check-update`: non-blocking check for a newer dlss-combo release before
  any command — prints one line and continues; network failures degrade to a
  skip notice. Evidence: `src/dlss_combo/update.py`, `tests/test_update.py`.
- Multi-GPU enumeration: all NVIDIA cards are parsed and the **first card
  with a supported architecture (RTX 20/30)** is selected; `doctor` lists
  multi-card rigs and names the primary. `--arch` still overrides.
  Evidence: `src/dlss_combo/gpu.py`, `tests/test_gpu_multi.py`.
- Recommended test-games list for RTX 20/30 testers, with native-FG
  evidence links and a verify-in-game disclaimer. Evidence:
  `docs/TEST-GAMES.md`.

### Changed

- **CLI is now English-only** — help text, diagnostics and error messages.
  Internal source comments are unchanged. Guarded by
  `tests/test_english_cli.py` (CJK scan over user-facing strings).
- Doctor session diagnostics hardened (see Fixed).

### Fixed

- Unreadable route logs are reported as problems instead of crashing
  `doctor`; the session verdict is now the **last route event of the newest
  log** (a later failure is never hidden by an earlier success), and
  image-layer files count as evidence only, never as layer activation.
  Evidence: `tests/test_doctor_last_event.py`.
- Manifest schema/path validation error messages are now English — translated
  wording only, failure behavior is unchanged — and a bare invocation prints
  usage again (guarded in `tests/test_english_cli.py`).
- Proxy fallback order regression-locked to the upstream tool-class order
  (`version → winmm → dbghelp → dinput8` before `d3d12`/`dxgi`).
  Evidence: `tests/test_proxy_order.py`.

## [0.1.3] — 2026-09-20

### Fixed

- Corrected release for v0.1.2's Linux measurement defect: the v0.1.2
  workflow's embedded-library extraction silently failed (wrong
  `CArchiveReader.extract` call signature) and fell back to the outer-file
  string scan, so `build-info.txt` again reported the under-stated floor
  (2.14). The step now uses the bytes-returning extraction API and **fails
  loudly when zero embedded ELF libraries parse** (no silent fallback). The
  real floor (expected 2.35, from the embedded libpython3.13) is recorded per
  build. v0.1.2 assets are left untouched; prefer this release.

## [0.1.2] — 2026-09-20

### Fixed (independent v0.1.1 review, R1–R7)

- **R1**: first-install failures now restore the user's original INI at every
  failure point (DLL copy, manifest write, backup write; reinstall failures
  restore the previous working state). Covered by fault-injection tests in
  `tests/test_review4.py`.
- **R2**: uninstall never overwrites any existing file or symlink when saving
  a restore copy — copies are created exclusively (`O_CREAT|O_EXCL`) with
  numbered fallback names (`*.pre-existing.1`, …).
- **R3**: temporary files use random, exclusively-created names
  (`tempfile.mkstemp`, same directory) — predictable-name symlink attacks are
  inert — and cleanup touches only paths registered by the current operation.
- **R4**: the Linux glibc floor is now measured by extracting the embedded
  ELF libraries from the PyInstaller CArchive and parsing their
  `.gnu.version_r` requirements (outer-file string scans under-report);
  docs state the real floor (**glibc >= 2.35**, from the embedded
  libpython3.13) and the release notes read the measured value per build.
- **R5**: a missing or corrupted pre-existing backup aborts uninstall before
  any deletion (backups now record a SHA256 that is verified when present).
- **R6**: doctor treats the newest log as the diagnostic scope; a newer
  session without route events reports "未验证/unverified" while older
  route events are labelled historical.
- **R7**: kit refreshes download into a staging directory and switch only
  after every file is fetched — an interrupted refresh leaves the previous
  kit fully valid (offline fallback preserved).

The eight reproduced scenarios from
[`docs/reviews/2026-09-20-v0.1.1-independent-repro.py`](docs/reviews/2026-09-20-v0.1.1-independent-repro.py)
all assert fixed, and are migrated into formal regressions
(`tests/test_review4.py`). Docs consistency: STATUS links/counts, README
quick-start no longer forces `--arch` (auto-detection first), Linux
requirements updated.

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

[0.2.0]: https://github.com/ztwzeroo/DLSS5-FrameGen/releases/tag/v0.2.0
[0.1.3]: https://github.com/ztwzeroo/DLSS5-FrameGen/releases/tag/v0.1.3
[0.1.2]: https://github.com/ztwzeroo/DLSS5-FrameGen/releases/tag/v0.1.2
[0.1.1]: https://github.com/ztwzeroo/DLSS5-FrameGen/releases/tag/v0.1.1
[0.1.0]: https://github.com/ztwzeroo/DLSS5-FrameGen/releases/tag/v0.1.0
