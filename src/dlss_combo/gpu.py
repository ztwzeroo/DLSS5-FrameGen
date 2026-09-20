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


def _parse_nvidia_smi(text: str) -> GpuInfo | None:
    """解析 `nvidia-smi --query-gpu=name,driver_version --format=csv` 风格输出；非 NVIDIA 或乱文返回 None。"""
    lines = [ln.strip() for ln in text.splitlines() if ln.strip()]
    if not lines or "name" not in lines[0].lower():
        return None
    if len(lines) < 2:
        return None
    parts = lines[1].split(",")
    name = parts[0].strip()
    driver = parts[1].strip() if len(parts) > 1 else None
    if not name.lower().startswith("nvidia"):
        return None
    arch: str | None = None
    for prefix, mapped in _NAME_ARCH_RULES:
        if prefix.lower() in name.lower():
            arch = mapped
            break
    return GpuInfo(
        vendor="nvidia", name=name, arch=arch, source="nvidia-smi", driver_version=driver
    )


def driver_meets_minimum(version: str | None) -> bool | None:
    """主版本号 ≥ R580 判定；无法解析返回 None（未知）。"""
    if not version:
        return None
    try:
        major = int(version.split(".")[0])
    except ValueError:
        return None
    return major >= MIN_DRIVER_MAJOR


def detect_gpu(
    override: str | None = None,
    runner: Callable[[str], str] | None = None,
) -> GpuInfo:
    """探测当前 GPU；override 指定架构（sm75/sm86/…）但不再跳过驱动探测。"""
    run = runner or _run_command
    info: GpuInfo | None = None
    try:
        info = _parse_nvidia_smi(run("nvidia-smi --query-gpu=name,driver_version --format=csv"))
    except (OSError, subprocess.SubprocessError):
        info = None
    if override:
        return GpuInfo(
            vendor="override", name=override, arch=override, source="override",
            driver_version=info.driver_version if info else None,
        )
    return info or GpuInfo(vendor="unknown", name="", arch=None, source="unknown")


def _run_command(cmd: str) -> str:
    result = subprocess.run(
        cmd.split(), capture_output=True, text=True, timeout=15, check=True
    )
    return result.stdout


def is_supported_arch(arch: str | None) -> bool:
    return arch in SUPPORTED
