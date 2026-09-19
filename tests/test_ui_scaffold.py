from pathlib import Path

from authkit.cli import build_parser


def test_ui_init_dry_run(tmp_path: Path, capsys) -> None:
    parser = build_parser()
    args = parser.parse_args(["ui", "init", "--framework", "nextjs", "--dir", str(tmp_path), "--dry-run"])
    args.handler(args)
    out = capsys.readouterr().out
    assert "login/page.tsx" in out
    assert "written" in out
    assert not (tmp_path / "app").exists()


def test_ui_init_preserves_files_unless_force_is_explicit(tmp_path: Path) -> None:
    parser = build_parser()
    args = parser.parse_args(["ui", "init", "--framework", "nextjs", "--dir", str(tmp_path)])
    args.handler(args)
    login = tmp_path / "app" / "(auth)" / "login" / "page.tsx"
    assert login.is_file()

    login.write_text("consumer-owned", encoding="utf-8")
    args.handler(args)
    assert login.read_text(encoding="utf-8") == "consumer-owned"

    force_args = parser.parse_args(
        ["ui", "init", "--framework", "nextjs", "--dir", str(tmp_path), "--force"]
    )
    force_args.handler(force_args)
    assert login.read_text(encoding="utf-8") != "consumer-owned"
