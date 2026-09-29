"""GPU 探测适配器：nvidia-smi 输出 → 显卡架构（sm75/sm86/…），可注入 runner 供测试。"""
import subprocess
from dataclasses import dataclass
from typing import Callable

SUPPORTED = {"sm75", "sm86"}  # dlssg_for_sm86 目标：RTX 20 (Turing) / RTX 30 (Ampere)
MIN_DRIVER_MAJOR = 580  # 上游 README：内核需 R580+，更低版本回退 PTX（首帧 JIT 慢）

# 显卡名 → 架构。按系列前缀匹配，从长前缀到短前缀。
_NAME_ARCH_RULES: list[tuple[str, str]] = [
    ("GeForce RTX 50", "sm120"),
    ("GeForce RTX 40", "sm89"),
    ("GeForce RTX 30", "sm86"),
    ("GeForce RTX 20", "sm75"),
    ("TITAN RTX", "sm75"),
    ("RTX A", "sm86"),   # Ampere 专业卡 A10/A40 等
    ("A100", "sm80"),
]


@dataclass
class GpuInfo:
    vendor: str
    name: str
    arch: str | None
    source: str  # "nvidia-smi" | "override" | "unknown"
    driver_version: str | None = None


def parse_nvidia_smi_all(text: str) -> list[GpuInfo]:
    """解析 `nvidia-smi --query-gpu=name,driver_version --format=csv` 风格输出；
    逐行枚举所有 NVIDIA 卡，跳过非 NVIDIA 行；乱文（无表头）返回空列表。"""
    lines = [ln.strip() for ln in text.splitlines() if ln.strip()]
    if not lines or "name" not in lines[0].lower():
        return []
    gpus: list[GpuInfo] = []
    for ln in lines[1:]:
        parts = ln.split(",")
        name = parts[0].strip()
        driver = parts[1].strip() if len(parts) > 1 else None
        if not name.lower().startswith("nvidia"):
            continue
        arch: str | None = None
        for prefix, mapped in _NAME_ARCH_RULES:
            if prefix.lower() in name.lower():
                arch = mapped
                break
        gpus.append(
            GpuInfo(vendor="nvidia", name=name, arch=arch, source="nvidia-smi", driver_version=driver)
        )
    return gpus


def _parse_nvidia_smi(text: str) -> GpuInfo | None:
    """旧单卡语义 = 多卡解析的第一行；tests/test_gpu.py 仍在用，保留薄包装。"""
    gpus = parse_nvidia_smi_all(text)
    return gpus[0] if gpus else None


def driver_meets_minimum(version: str | None) -> bool | None:
    """主版本号 ≥ R580 判定；无法解析返回 None（未知）。"""
    if not version:
        return None
    try:
        major = int(version.split(".")[0])
    except ValueError:
        return None
    return major >= MIN_DRIVER_MAJOR


def detect_all_gpus(runner: Callable[[str], str] | None = None) -> list[GpuInfo]:
    """枚举本机全部 GPU；nvidia-smi 缺失/执行失败/乱输出统一返回空列表。"""
    run = runner or _run_command
    try:
        return parse_nvidia_smi_all(run("nvidia-smi --query-gpu=name,driver_version --format=csv"))
    except Exception:  # FileNotFoundError / SubprocessError / 注入 runner 抛错等，探测永不致命
        return []


def choose_gpu(gpus: list[GpuInfo]) -> GpuInfo:
    """多卡择主：第一张受支持架构的 NVIDIA 卡 → 第一张 NVIDIA 卡 → unknown。"""
    nvidia = [g for g in gpus if g.vendor == "nvidia"]
    for g in nvidia:
        if is_supported_arch(g.arch):
            return g
    if nvidia:
        return nvidia[0]
    return GpuInfo(vendor="unknown", name="", arch=None, source="unknown")


def detect_gpu(
    override: str | None = None,
    runner: Callable[[str], str] | None = None,
) -> GpuInfo:
    """探测当前 GPU；多卡时选第一张受支持架构的卡；
    override 指定架构（sm75/sm86/…）但不再跳过驱动探测。"""
    info = choose_gpu(detect_all_gpus(runner))
    if override:
        return GpuInfo(
            vendor="override", name=override, arch=override, source="override",
            driver_version=info.driver_version,
        )
    return info


def _run_command(cmd: str) -> str:
    result = subprocess.run(
        cmd.split(), capture_output=True, text=True, timeout=15, check=True
    )
    return result.stdout


def is_supported_arch(arch: str | None) -> bool:
    return arch in SUPPORTED
