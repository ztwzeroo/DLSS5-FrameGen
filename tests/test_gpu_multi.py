"""W3: enumerate every nvidia-smi row; pick the first SUPPORTED NVIDIA card."""
from dlss_combo.gpu import choose_gpu, detect_all_gpus, detect_gpu, parse_nvidia_smi_all


def _csv(*rows: str) -> str:
    return "name, driver_version\n" + "\n".join(rows)


GT710 = "NVIDIA GeForce GT 710, 580.88"
RTX3060 = "NVIDIA GeForce RTX 3060 Laptop GPU, 581.09"
RTX4090 = "NVIDIA GeForce RTX 4090, 580.66"


def test_parses_all_rows_and_skips_non_nvidia():
    gpus = parse_nvidia_smi_all(_csv("Intel(R) Iris Xe, 31.0", GT710, RTX3060))
    assert [g.name for g in gpus] == [GT710.split(",")[0], RTX3060.split(",")[0]]


def test_choose_prefers_first_supported_over_older_card_first():
    gpus = parse_nvidia_smi_all(_csv(GT710, RTX3060))
    assert choose_gpu(gpus).arch == "sm86"


def test_choose_prefers_supported_over_newer_unsupported():
    gpus = parse_nvidia_smi_all(_csv(RTX4090, RTX3060))
    assert choose_gpu(gpus).arch == "sm86"


def test_all_unsupported_falls_back_to_first_nvidia():
    gpus = parse_nvidia_smi_all(_csv(GT710, RTX4090))
    assert choose_gpu(gpus).name.startswith("NVIDIA GeForce GT 710")


def test_detect_all_gpus_runner_failure_returns_empty():
    def boom(cmd):
        raise RuntimeError("no nvidia-smi")
    assert detect_all_gpus(runner=boom) == []
    assert choose_gpu([]).vendor == "unknown"


def test_detect_gpu_delegates_and_keeps_override():
    assert detect_gpu(runner=lambda c: _csv(RTX4090, RTX3060)).arch == "sm86"
    assert detect_gpu(override="sm75", runner=lambda c: _csv(RTX3060)).arch == "sm75"


def test_doctor_lists_multiple_nvidia_cards(tmp_path, monkeypatch):
    import dlss_combo.doctor as doc
    monkeypatch.setattr(doc, "detect_all_gpus", lambda runner=None: parse_nvidia_smi_all(_csv(GT710, RTX3060)))
    rep = doc.doctor(tmp_path)
    assert any("multiple NVIDIA GPUs" in ln for ln in rep.lines)
    assert any("RTX 3060" in ln for ln in rep.lines)
