import configparser

import pytest

from dlss_combo.ini import MFG_PRESET, build_ini


def _parse(text: str) -> configparser.ConfigParser:
    cp = configparser.ConfigParser(strict=False)
    cp.read_string(text)
    return cp


def test_defaults():
    cp = _parse(build_ini())
    assert cp["General"]["Enabled"] == "1"
    assert cp["FrameGeneration"]["Optimized"] == "1"
    assert cp["FrameGeneration"]["MaxGeneratedFrames"] == "3"  # 4x
    assert cp["Compatibility"]["Preset"] == "Auto"
    assert cp["Logging"]["Level"] == "1"
    assert cp["Logging"]["Directory"] == "dlssg_sm86\\logs"
    assert cp["Runtime"]["Mode"] == "Bundled"


def test_6x_tier2_verbose_logging():
    cp = _parse(build_ini(tier=2, mfg="6x", logging_level=2))
    assert cp["FrameGeneration"]["MaxGeneratedFrames"] == "5"
    assert cp["FrameGeneration"]["Optimized"] == "2"
    assert cp["Logging"]["Level"] == "2"


def test_invalid_args_raise():
    with pytest.raises(ValueError):
        build_ini(tier=4)
    with pytest.raises(ValueError):
        build_ini(tier=-1)
    with pytest.raises(ValueError):
        build_ini(mfg="9x")


def test_mfg_preset_table():
    assert MFG_PRESET == {"2x": 1, "3x": 2, "4x": 3, "6x": 5}


def test_bilingual_header_present():
    text = build_ini()
    assert "dlss-combo" in text
    assert "dlssg_sm86\\logs" in text
