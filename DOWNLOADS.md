# Downloads & manual file placement

[← Back to the project](README.md)

`dlss-combo fetch` downloads everything below automatically, verifies it, and
caches it. **This page is the manual fallback** for when scripted downloads are
impossible. It is also the honest answer to "why isn't everything in one zip":

> The frame-generation DLLs embed **NVIDIA's DLSS-G runtime**, and the Swapper
> portable app contains NVIDIA's neural-rendering library. NVIDIA's SDK terms do
> not allow us to redistribute those binaries inside our release packages, so
> this project links to the **upstream official channels** and fetches from them
> at install time. We never re-host or modify upstream files.

## 1. Frame-generation kit — [sdli1995/dlssg_for_sm86](https://github.com/sdli1995/dlssg_for_sm86)

GPLv3 source (license declared in the upstream README); the embedded NVIDIA
runtime inside these DLLs is NVIDIA's, not ours or upstream's to relicense.

Download these files from the repository (paths below are on `main`; `fetch`
pins the exact commit and records it in `kit.json`):

| Kit file | Runtime 310.9 (repo root) | Runtime 310.1 (repo `310.1/`) |
|---|---|---|
| main proxy | [`version.dll`](https://github.com/sdli1995/dlssg_for_sm86/raw/main/version.dll) | [`310.1/version.dll`](https://github.com/sdli1995/dlssg_for_sm86/raw/main/310.1/version.dll) |
| INI template | [`dlssg_sm86.ini`](https://github.com/sdli1995/dlssg_for_sm86/raw/main/dlssg_sm86.ini) | [`310.1/dlssg_sm86.ini`](https://github.com/sdli1995/dlssg_for_sm86/raw/main/310.1/dlssg_sm86.ini) |
| alternative names | [`alternatives/winmm.dll`](https://github.com/sdli1995/dlssg_for_sm86/raw/main/alternatives/winmm.dll) · [`d3d12.dll`](https://github.com/sdli1995/dlssg_for_sm86/raw/main/alternatives/d3d12.dll) · [`dbghelp.dll`](https://github.com/sdli1995/dlssg_for_sm86/raw/main/alternatives/dbghelp.dll) · [`dinput8.dll`](https://github.com/sdli1995/dlssg_for_sm86/raw/main/alternatives/dinput8.dll) · [`dxgi.dll`](https://github.com/sdli1995/dlssg_for_sm86/raw/main/alternatives/dxgi.dll) | same names under [`310.1/alternatives/`](https://github.com/sdli1995/dlssg_for_sm86/tree/main/310.1/alternatives) |

Place them so your kit directory looks like (default kit: `~/dlss-combo-kit`):

```text
<kit>/dlssg/310.9/version.dll
<kit>/dlssg/310.9/dlssg_sm86.ini
<kit>/dlssg/310.9/alternatives/{winmm,d3d12,dbghelp,dinput8,dxgi}.dll
<kit>/dlssg/310.1/…            (same layout)
```

## 2. Image layer — [DLSS5-Swapper](https://github.com/rakanki911/DLSS5-Swapper) (MIT app)

Download the **portable** build from its
[latest release](https://github.com/rakanki911/DLSS5-Swapper/releases/latest)
(`DLSS5Swapper-*-portable.exe`; ignore the Setup installer), then either run it
directly or let the kit manage it:

```text
<kit>/swapper/DLSS5Swapper-<version>-portable.exe
```

## 3. The toolkit itself

Prebuilt `dlss-combo` binaries for Windows x64 and Linux x64 are on our
[Releases](releases/latest) page with `SHA256SUMS.txt` — that part is our code
(MIT) and we do ship it.

## Slow or blocked GitHub? Mirrors

`fetch` tries official sources first (`raw.githubusercontent.com`, then
`github.com/<repo>/raw/…`) and only falls back to community mirrors of those
same URLs afterwards. You can set your own mirror list:

```bash
export DLSS_COMBO_MIRRORS="https://your-mirror.example/,https://another.example/"
```

Default mirrors: `https://gh-proxy.com/`, `https://ghproxy.net/` — they proxy
the official URLs above; files are still hash-recorded locally on download
(`kit.json`, local integrity baseline — upstream publishes no checksums for
these assets, and mirrors are third parties, so treat official sources as the
source of truth when reachable).

## Integrity

Every file the tool installs is SHA256-recorded at download time and re-verified
on every later run (`doctor`, reinstall, launch). Manual downloads are accepted
by `fetch` as cache hits only after the same checks.
