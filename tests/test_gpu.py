from dlss_combo.gpu import SUPPORTED, _parse_nvidia_smi, detect_gpu

SMI_3070 = "name, driver_version\nNVIDIA GeForce RTX 3070, 591.86\n"
SMI_2080TI = "name, driver_version\nNVIDIA GeForce RTX 2080 Ti, 601.05\n"
SMI_5070 = "name, driver_version\nNVIDIA GeForce RTX 5070, 610.74\n"
SMI_AMD = "name, driver_version\nAMD Radeon RX 7900 XTX, 34.1\n"


def test_parse_sm86():
    g = _parse_nvidia_smi(SMI_3070)
    assert g is not None
    assert g.arch == "sm86"
    assert g.vendor == "nvidia"
    assert g.name == "NVIDIA GeForce RTX 3070"


def test_parse_sm75():
    g = _parse_nvidia_smi(SMI_2080TI)
    assert g is not None and g.arch == "sm75"


def test_unsupported_arch_detected():
    g = _parse_nvidia_smi(SMI_5070)
    assert g is not None and g.arch == "sm120" and g.arch not in SUPPORTED


def test_non_nvidia_returns_none():
    assert _parse_nvidia_smi(SMI_AMD) is None


def test_garbage_returns_none():
    assert _parse_nvidia_smi("ls: cannot access") is None


def test_override_wins():
    g = detect_gpu(override="sm86")
    assert g.arch == "sm86" and g.source == "override"


def test_no_tool_yields_unknown():
    def boom(cmd):
        raise FileNotFoundError("no nvidia-smi")

    g = detect_gpu(runner=boom)
    assert g.source == "unknown" and g.arch is None


def test_runner_injection():
    g = detect_gpu(runner=lambda cmd: SMI_3070)
    assert g.arch == "sm86" and g.source == "nvidia-smi"
