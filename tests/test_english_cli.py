"""W6 guard: user-facing strings are English-only."""
import re
from pathlib import Path

SRC = Path(__file__).resolve().parents[1] / "src" / "dlss_combo"
CJK = re.compile(r"[\u4e00-\u9fff]")
USER_FACING_LINE = re.compile(r"(print\s*\(|help\s*=\s*['\"]|description\s*=\s*['\"]|epilog\s*=\s*['\"])")


def test_no_cjk_in_inline_user_facing_strings():
    offenders = []
    for f in sorted(SRC.glob("*.py")):
        for i, ln in enumerate(f.read_text(encoding="utf-8").splitlines(), 1):
            if CJK.search(ln) and USER_FACING_LINE.search(ln):
                offenders.append(f"{f.name}:{i}: {ln.strip()}")
    assert not offenders, "user-facing strings must be English:\n" + "\n".join(offenders)


def test_help_and_doctor_output_english(tmp_path):
    from dlss_combo.cli import _build_parser
    from dlss_combo.doctor import doctor
    assert not CJK.search(_build_parser().format_help())
    (tmp_path / "ReShade.ini").write_text("[GENERAL]\n", encoding="utf-8")
    assert not CJK.search("\n".join(doctor(tmp_path).lines))
