"""
Tests for CLI module.
"""

from pathlib import Path
from click.testing import CliRunner
import pytest

from wp_migration_verifier.cli import main


def test_cli_identical_dirs(identical_dirs, temp_dir: Path):
    """Test CLI with identical directories."""
    source, dest = identical_dirs
    output = temp_dir / "report.json"

    runner = CliRunner()
    result = runner.invoke(main, [str(source), str(dest), "-o", str(output)])

    assert result.exit_code == 0
    assert output.exists()
    assert "Report written to" in result.output


def test_cli_different_dirs(different_dirs, temp_dir: Path):
    """Test CLI with different directories (should exit with code 1)."""
    source, dest = different_dirs
    output = temp_dir / "report.json"

    runner = CliRunner()
    result = runner.invoke(main, [str(source), str(dest), "-o", str(output)])

    assert result.exit_code == 1
    assert output.exists()


def test_cli_no_hash(different_dirs, temp_dir: Path):
    """Test CLI with --no-hash flag."""
    source, dest = different_dirs
    output = temp_dir / "report.json"

    runner = CliRunner()
    result = runner.invoke(main, [str(source), str(dest), "-o", str(output), "--no-hash"])

    assert result.exit_code == 1
    assert output.exists()

    import json
    data = json.loads(output.read_text())
    # Without hashing, same-size files are "size-matched" (content not verified)
    # style.css has different content but same size in our fixture
    assert data["summary"]["size-matched"] >= 1


def test_cli_include_identical(identical_dirs, temp_dir: Path):
    """Test CLI with --include-identical flag."""
    source, dest = identical_dirs
    output = temp_dir / "report.json"

    runner = CliRunner()
    result = runner.invoke(main, [str(source), str(dest), "-o", str(output), "--include-identical"])

    assert result.exit_code == 0

    import json
    data = json.loads(output.read_text())
    assert len(data["details"]) > 0  # Should include identical files


def test_cli_nonexistent_source(temp_dir: Path):
    """Test CLI with nonexistent source."""
    dest = temp_dir / "dest"
    dest.mkdir()

    runner = CliRunner()
    result = runner.invoke(main, [str(temp_dir / "nonexistent"), str(dest)])

    assert result.exit_code != 0
    assert "Error" in result.output or "not exist" in result.output.lower()


def test_cli_not_a_directory(temp_dir: Path):
    """Test CLI with file instead of directory."""
    source = temp_dir / "source"
    source.mkdir()
    (source / "file.txt").write_text("content")
    dest = temp_dir / "dest"
    dest.mkdir()

    runner = CliRunner()
    result = runner.invoke(main, [str(source / "file.txt"), str(dest)])

    assert result.exit_code != 0


def test_cli_quiet_flag(identical_dirs, temp_dir: Path):
    """Test CLI with --quiet flag."""
    source, dest = identical_dirs
    output = temp_dir / "report.json"

    runner = CliRunner()
    result = runner.invoke(main, [str(source), str(dest), "-o", str(output), "-q"])

    assert result.exit_code == 0
    assert result.output.strip() == ""  # No output in quiet mode


def test_cli_help():
    """Test CLI help output."""
    runner = CliRunner()
    result = runner.invoke(main, ["--help"])

    assert result.exit_code == 0
    assert "Verify WordPress migration" in result.output
    assert "--no-hash" in result.output
    assert "--include-identical" in result.output


def test_cli_markdown_flag(different_dirs, temp_dir: Path):
    """Test CLI with --markdown flag creates .md file."""
    source, dest = different_dirs
    output = temp_dir / "report.json"

    runner = CliRunner()
    result = runner.invoke(main, [str(source), str(dest), "-o", str(output), "--markdown"])

    assert result.exit_code == 1
    assert output.exists()
    md_path = temp_dir / "report.md"
    assert md_path.exists()
    md_content = md_path.read_text(encoding="utf-8")
    assert "# WP Migration Integrity Report" in md_content
    assert "Review Required" in md_content
    assert "## Detailed Changes" in md_content
    assert "Markdown report written to" in result.output


def test_cli_without_markdown_flag(different_dirs, temp_dir: Path):
    """Test CLI without --markdown flag does not create .md file."""
    source, dest = different_dirs
    output = temp_dir / "report.json"

    runner = CliRunner()
    result = runner.invoke(main, [str(source), str(dest), "-o", str(output)])

    assert result.exit_code == 1
    assert output.exists()
    md_path = temp_dir / "report.md"
    assert not md_path.exists()


def test_cli_markdown_quiet(different_dirs, temp_dir: Path):
    """Test CLI with --markdown and --quiet suppresses output."""
    source, dest = different_dirs
    output = temp_dir / "report.json"

    runner = CliRunner()
    result = runner.invoke(main, [str(source), str(dest), "-o", str(output), "--markdown", "-q"])

    assert result.exit_code == 1
    assert output.exists()
    md_path = temp_dir / "report.md"
    assert md_path.exists()
    assert result.output.strip() == ""


def test_cli_markdown_with_no_hash(different_dirs, temp_dir: Path):
    """Test CLI with --markdown and --no-hash shows size-matched."""
    source, dest = different_dirs
    output = temp_dir / "report.json"

    runner = CliRunner()
    result = runner.invoke(main, [str(source), str(dest), "-o", str(output), "--markdown", "--no-hash"])

    assert result.exit_code == 1
    md_path = temp_dir / "report.md"
    assert md_path.exists()
    md_content = md_path.read_text(encoding="utf-8")
    assert "Size-matched" in md_content
    assert "❌ Skipped (size only)" in md_content


def test_cli_markdown_with_include_identical(identical_dirs, temp_dir: Path):
    """Test CLI with --markdown and --include-identical shows identical files."""
    source, dest = identical_dirs
    output = temp_dir / "report.json"

    runner = CliRunner()
    result = runner.invoke(main, [str(source), str(dest), "-o", str(output), "--markdown", "--include-identical"])

    assert result.exit_code == 0
    md_path = temp_dir / "report.md"
    assert md_path.exists()
    md_content = md_path.read_text(encoding="utf-8")
    assert "Identical" in md_content
    # No file should have "Size-matched" status in the detailed changes table
    assert "`Size-matched`" not in md_content