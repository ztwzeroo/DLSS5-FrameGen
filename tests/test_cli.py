from pathlib import Path

from dlss_combo.cli import main


def test_install_via_cli(game: Path, kit: Path, capsys):
    rc = main(
        ["install", str(game), "--kit-dir", str(kit), "--arch", "sm86", "--mfg", "4x"]
    )
    assert rc == 0
    assert (game / "version.dll").exists()
    out = capsys.readouterr().out
    assert "55" in out  # 调优指引含基础帧率建议


def test_unsupported_arch_cli_fails(game: Path, kit: Path):
    rc = main(["install", str(game), "--kit-dir", str(kit), "--arch", "sm120"])
    assert rc != 0


def test_missing_game_dir_cli_fails(tmp_path: Path):
    rc = main(["install", str(tmp_path / "nowhere"), "--kit-dir", str(tmp_path), "--arch", "sm86"])
    assert rc != 0


def test_doctor_via_cli_on_missing_dir(tmp_path: Path):
    rc = main(["doctor", str(tmp_path / "nowhere")])
    assert rc != 0


def test_doctor_via_cli_ok(game: Path, kit: Path, capsys):
    main(["install", str(game), "--kit-dir", str(kit), "--arch", "sm86"])
    rc = main(["doctor", str(game)])
    assert rc == 0
    assert "dlssg" in capsys.readouterr().out


def test_uninstall_via_cli(game: Path, kit: Path):
    main(["install", str(game), "--kit-dir", str(kit), "--arch", "sm86"])
    assert main(["uninstall", str(game)]) == 0
    assert not (game / "version.dll").exists()


def test_uninstall_without_manifest_cli_fails(tmp_path: Path):
    assert main(["uninstall", str(tmp_path)]) != 0


def test_invalid_mfg_rejected(game: Path, kit: Path):
    rc = main(["install", str(game), "--kit-dir", str(kit), "--arch", "sm86", "--mfg", "9x"])
    assert rc != 0
