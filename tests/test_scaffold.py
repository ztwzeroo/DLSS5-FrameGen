import importlib.metadata

import dlss_combo


def test_package_version_single_source():
    assert dlss_combo.__version__ == "0.1.1"
    # 安装态（pip/PyInstaller 打包取同一字面量）与包内声明一致
    try:
        assert importlib.metadata.version("dlss-combo") == dlss_combo.__version__
    except importlib.metadata.PackageNotFoundError:
        pass
