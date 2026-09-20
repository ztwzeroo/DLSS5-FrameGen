"""Read-only project audit: all file mutations are confined to temporary fixtures."""
import hashlib
import json
import sys
import tempfile
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / 'src'))
from dlss_combo.fetch import fetch_kit, verify_kit, launch_swapper
from dlss_combo.install import install
from dlss_combo.uninstall import uninstall
from dlss_combo.manifest import Manifest
from dlss_combo.doctor import doctor, _parse_route_active

results = []
def record(case, observed):
    results.append({'case': case, 'observed': observed})

def kit_at(root):
    def fake(url):
        if url.endswith('commits/main'):
            return b'{"sha":"audit-commit"}'
        return ('fixture:' + url.rsplit('/', 1)[-1]).encode()
    kit = root / 'kit'
    fetch_kit(kit, fetch_bytes=fake)
    return kit

with tempfile.TemporaryDirectory(prefix='dlss-audit-') as tmp:
    root = Path(tmp)
    kit = kit_at(root)
    def game(name):
        p = root / name
        p.mkdir()
        return p

    g = game('uninstall-traversal')
    outside = root / 'outside-sentinel.txt'
    outside.write_text('keep')
    m = Manifest()
    m.record_file('../outside-sentinel.txt', m.sha256_of(outside), 'kit')
    m.save(g)
    try:
        uninstall(g)
        deleted = not outside.exists()
    except ValueError:
        deleted = False  # 修复后：非法清单被拒绝，目录外文件保留
    record('uninstall deletes outside game directory', deleted)

    g = game('foreign-ini')
    ini = g / 'dlssg_sm86.ini'
    ini.write_text('; original custom settings')
    install(g, kit, arch='sm86')
    overwritten = ini.read_text() != '; original custom settings'
    uninstall(g)
    record('preexisting INI overwritten and lost after uninstall', overwritten and not ini.exists())

    g = game('replaced-dll')
    install(g, kit, arch='sm86')
    dll = g / 'version.dll'
    dll.write_bytes(b'new third party mod')
    install(g, kit, arch='sm86')
    overwritten = dll.read_bytes() != b'new third party mod'
    uninstall(g)
    record('third party replacement overwritten and backup erased on uninstall', overwritten and not (g / '.dlss-combo').exists())

    meta_path = kit / 'kit.json'
    original = meta_path.read_text()
    meta = json.loads(original)
    meta['files'] = {}
    meta_path.write_text(json.dumps(meta))
    record('empty checksum map passes verify_kit', verify_kit(kit) == [])
    meta_path.write_text(original)

    g = game('partial-copy')
    install(g, kit, arch='sm86')
    import shutil
    original_copy = shutil.copy2
    def broken_copy(src, dst, *args, **kwargs):
        if Path(src) == kit / 'dlssg/310.9/version.dll':
            Path(dst).write_bytes(b'PARTIAL')
            raise OSError('simulated disk full after partial write')
        return original_copy(src, dst, *args, **kwargs)
    with patch('dlss_combo.install.shutil.copy2', side_effect=broken_copy):
        try:
            install(g, kit, arch='sm86')
        except OSError:
            pass
    record('partial copy leaves corrupt DLL instead of rollback', (g / 'version.dll').read_bytes() == b'PARTIAL')

    record('doctor uses first route in same log', _parse_route_active('{"route":{"active":true}}\n{"route":{"active":false}}') is True)
    g = game('reshade-only')
    (g / 'reshade-shaders').mkdir()
    record('empty ReShade folder reported as DLSS 5 installed', any('OK: 检测到 DLSS 5' in s for s in doctor(g).lines))

    meta = json.loads(original)
    exe = kit / 'swapper/portable.exe'
    exe.parent.mkdir()
    exe.write_bytes(b'original exe')
    meta['swapper'] = {'zip':'swapper/portable.exe', 'tag':'audit', 'sha256':hashlib.sha256(exe.read_bytes()).hexdigest()}
    meta_path.write_text(json.dumps(meta))
    exe.write_bytes(b'modified exe')
    launched = []
    try:
        launch_swapper(kit, spawn=launched.append)
    except RuntimeError:
        pass  # 修复后：哈希不符拒绝启动
    record('changed Swapper passed to launcher without hash check', launched == [exe])
    fetch_kit(kit, refresh=True, fetch_bytes=lambda url: b'{"sha":"next-commit"}' if url.endswith('commits/main') else b'new fixture')
    record('kit refresh drops Swapper metadata', 'swapper' not in json.loads(meta_path.read_text()))

print(json.dumps(results, ensure_ascii=False, indent=2))
# 修复后语义：observed=False 表示缺陷已消除；全部为 False 即修复完成。
assert not any(r['observed'] for r in results), 'Some issues are STILL present: ' + str(
    [r['case'] for r in results if r['observed']])
