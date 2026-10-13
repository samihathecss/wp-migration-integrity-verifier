"""
Tests for report module.
"""

import json
from pathlib import Path

from wp_migration_verifier.report import generate_report, generate_markdown, write_report
from wp_migration_verifier.compare import ComparisonResult, DiffEntry


def test_generate_report_basic(temp_dir: Path):
    """Test basic report generation."""
    entries = [
        DiffEntry(path=Path("file1.txt"), status="identical", source_hash="abc", dest_hash="abc", source_size=10, dest_size=10),
        DiffEntry(path=Path("file2.txt"), status="missing", source_hash="def", source_size=20),
        DiffEntry(path=Path("file3.txt"), status="added", dest_hash="ghi", dest_size=30),
        DiffEntry(path=Path("file4.txt"), status="changed", source_hash="aaa", dest_hash="bbb", source_size=40, dest_size=40),
        DiffEntry(path=Path("file5.txt"), status="error", error="unreadable"),
    ]
    result = ComparisonResult(entries=entries, summary={
        "total": 5,
        "identical": 1,
        "missing": 1,
        "added": 1,
        "changed": 1,
        "error": 1,
        "skipped": 0,
    })

    report = generate_report(result, include_identical=True)

    assert report["summary"]["total"] == 5
    assert report["summary"]["identical"] == 1
    assert report["summary"]["missing"] == 1
    assert report["summary"]["added"] == 1
    assert report["summary"]["changed"] == 1
    assert report["summary"]["error"] == 1
    assert len(report["details"]) == 5
    assert "note" in report
    assert "file comparison only" in report["note"].lower()
    # New verification fields
    assert "verification" in report
    assert report["verification"]["differences_found"] is True
    assert report["verification"]["files_missing"] == 1
    assert report["verification"]["files_added"] == 1
    assert report["verification"]["files_changed"] == 1
    assert report["verification"]["files_skipped"] == 0
    assert report["verification"]["hash_verified"] is True
    assert report["verification"]["review_required"] is True
    assert "limitations" in report["verification"]
    assert len(report["verification"]["limitations"]) == 3


def test_generate_report_no_differences(temp_dir: Path):
    """Test report when all files are identical."""
    entries = [
        DiffEntry(path=Path("file1.txt"), status="identical", source_hash="abc", dest_hash="abc", source_size=10, dest_size=10),
        DiffEntry(path=Path("file2.txt"), status="identical", source_hash="def", dest_hash="def", source_size=20, dest_size=20),
    ]
    result = ComparisonResult(entries=entries, summary={
        "total": 2,
        "identical": 2,
        "missing": 0,
        "added": 0,
        "changed": 0,
        "error": 0,
        "skipped": 0,
    })

    report = generate_report(result, include_identical=True, hash_files=True)

    assert report["verification"]["differences_found"] is False
    assert report["verification"]["review_required"] is False
    assert report["verification"]["hash_verified"] is True


def test_generate_report_no_hash(temp_dir: Path):
    """Test report when hashing is disabled."""
    entries = [
        DiffEntry(path=Path("file1.txt"), status="size-matched", source_hash=None, dest_hash=None, source_size=10, dest_size=10),
    ]
    result = ComparisonResult(entries=entries, summary={
        "total": 1,
        "size-matched": 1,
        "identical": 0,
        "missing": 0,
        "added": 0,
        "changed": 0,
        "error": 0,
        "skipped": 0,
    })

    report = generate_report(result, include_identical=True, hash_files=False)

    assert report["verification"]["hash_verified"] is False
    assert report["verification"]["differences_found"] is False
    assert report["verification"]["review_required"] is False


def test_generate_report_with_skipped(temp_dir: Path):
    """Test report with skipped (sensitive) files."""
    entries = [
        DiffEntry(path=Path("wp-config.php"), status="skipped"),
        DiffEntry(path=Path("normal.txt"), status="identical", source_hash="abc", dest_hash="abc"),
    ]
    result = ComparisonResult(entries=entries, summary={
        "total": 2,
        "identical": 1,
        "skipped": 1,
        "missing": 0,
        "added": 0,
        "changed": 0,
        "error": 0,
    })

    report = generate_report(result, include_identical=True, hash_files=True)

    assert report["verification"]["files_skipped"] == 1
    assert report["verification"]["review_required"] is True  # skipped files require review
    assert report["verification"]["differences_found"] is False


def test_generate_report_exclude_identical(temp_dir: Path):
    """Test report generation with identical files excluded."""
    entries = [
        DiffEntry(path=Path("same.txt"), status="identical", source_hash="abc", dest_hash="abc"),
        DiffEntry(path=Path("diff.txt"), status="changed", source_hash="aaa", dest_hash="bbb"),
    ]
    result = ComparisonResult(entries=entries, summary={
        "total": 2,
        "identical": 1,
        "changed": 1,
    })

    report = generate_report(result, include_identical=False)
    assert len(report["details"]) == 1
    assert report["details"][0]["path"] == "diff.txt"

    report_all = generate_report(result, include_identical=True)
    assert len(report_all["details"]) == 2


def test_write_report(temp_dir: Path):
    """Test writing report to file."""
    entries = [
        DiffEntry(path=Path("test.txt"), status="identical", source_hash="abc", dest_hash="abc"),
    ]
    result = ComparisonResult(entries=entries, summary={"total": 1, "identical": 1})

    output = temp_dir / "report.json"
    write_report(result, output, include_identical=True)

    assert output.exists()
    data = json.loads(output.read_text())
    assert data["summary"]["total"] == 1
    assert data["details"][0]["path"] == "test.txt"
    assert "verification" in data
    assert data["verification"]["hash_verified"] is True


def test_report_json_structure(temp_dir: Path):
    """Test report has correct JSON structure."""
    entries = [
        DiffEntry(
            path=Path("wp-content/style.css"),
            status="changed",
            source_hash="aaa",
            dest_hash="bbb",
            source_size=100,
            dest_size=200
        ),
    ]
    result = ComparisonResult(entries=entries, summary={"total": 1, "changed": 1})

    report = generate_report(result)

    detail = report["details"][0]
    assert Path(detail["path"]) == Path("wp-content/style.css")
    assert detail["status"] == "changed"
    assert detail["source_hash"] == "aaa"
    assert detail["dest_hash"] == "bbb"
    assert detail["source_size"] == 100
    assert detail["dest_size"] == 200
    assert "error" not in detail


def test_report_includes_error_field():
    """Test error field is included when present."""
    entries = [
        DiffEntry(path=Path("bad.txt"), status="error", error="permission denied"),
    ]
    result = ComparisonResult(entries=entries, summary={"total": 1, "error": 1})

    report = generate_report(result)
    assert report["details"][0]["error"] == "permission denied"


# --- Markdown report tests ---

def test_generate_markdown_normal(temp_dir: Path):
    """Test markdown generation with normal differences."""
    entries = [
        DiffEntry(path=Path("file1.txt"), status="identical", source_hash="abc", dest_hash="abc", source_size=10, dest_size=10),
        DiffEntry(path=Path("file2.txt"), status="missing", source_hash="def", source_size=20),
        DiffEntry(path=Path("file3.txt"), status="added", dest_hash="ghi", dest_size=30),
        DiffEntry(path=Path("file4.txt"), status="changed", source_hash="aaa", dest_hash="bbb", source_size=40, dest_size=40),
    ]
    result = ComparisonResult(entries=entries, summary={
        "total": 4,
        "identical": 1,
        "missing": 1,
        "added": 1,
        "changed": 1,
    })

    md = generate_markdown(result, include_identical=True, hash_files=True)

    # Check structure
    assert "# WP Migration Integrity Report" in md
    assert "⚠️ **Review Required** — Differences found" in md
    assert "## Summary" in md
    assert "Missing in destination | 1" in md
    assert "Added in destination | 1" in md
    assert "Changed (content differs) | 1" in md
    assert "## Verification" in md
    assert "✅ Performed" in md  # hash_verified
    assert "## Limitations" in md
    assert "Database content not compared" in md
    assert "## Recommended Next Steps" in md
    assert "## Detailed Changes" in md
    # Check table rows
    assert "`file2.txt` | Missing | 20 bytes (source only)" in md
    assert "`file3.txt` | Added | 30 bytes (dest only)" in md
    assert "`file4.txt` | Changed | Hash differs (source: 40 bytes, dest: 40 bytes)" in md


def test_generate_markdown_no_differences(temp_dir: Path):
    """Test markdown when all files are identical."""
    entries = [
        DiffEntry(path=Path("file1.txt"), status="identical", source_hash="abc", dest_hash="abc", source_size=10, dest_size=10),
    ]
    result = ComparisonResult(entries=entries, summary={
        "total": 1,
        "identical": 1,
    })

    md = generate_markdown(result, include_identical=True, hash_files=True)

    assert "✅ **No Differences Found**" in md
    assert "⚠️" not in md
    assert "`file1.txt` | Identical | 10 bytes (hash verified)" in md
    assert "✅ Performed" in md


def test_generate_markdown_no_hash(temp_dir: Path):
    """Test markdown when hashing is disabled (size-matched)."""
    entries = [
        DiffEntry(path=Path("file1.txt"), status="size-matched", source_hash=None, dest_hash=None, source_size=10, dest_size=10),
    ]
    result = ComparisonResult(entries=entries, summary={
        "total": 1,
        "size-matched": 1,
    })

    md = generate_markdown(result, include_identical=True, hash_files=False)

    assert "❌ Skipped (size only)" in md  # hash_verified = false
    assert "size-matched" in md
    assert "Size-matched" in md  # status label
    assert "size matches, content not verified" in md


def test_generate_markdown_skipped_files(temp_dir: Path):
    """Test markdown with skipped (sensitive) files."""
    entries = [
        DiffEntry(path=Path("wp-config.php"), status="skipped"),
        DiffEntry(path=Path("normal.txt"), status="identical", source_hash="abc", dest_hash="abc"),
    ]
    result = ComparisonResult(entries=entries, summary={
        "total": 2,
        "identical": 1,
        "skipped": 1,
    })

    md = generate_markdown(result, include_identical=True, hash_files=True)

    assert "⚠️ **Review Required** — Sensitive files skipped" in md
    assert "Skipped | 1" in md
    assert "`wp-config.php` | Skipped | Excluded from comparison (sensitive pattern)" in md


def test_generate_markdown_escapes_pipes(temp_dir: Path):
    """Test that file paths with pipe characters are escaped in markdown table."""
    entries = [
        DiffEntry(path=Path("file|with|pipes.txt"), status="added", dest_hash="abc", dest_size=5),
    ]
    result = ComparisonResult(entries=entries, summary={
        "total": 1,
        "added": 1,
    })

    md = generate_markdown(result, include_identical=True, hash_files=True)

    # Pipe in path should be escaped
    assert "`file\\|with\\|pipes.txt`" in md
    # Table should not be broken
    assert md.count("|") >= 6  # header + separator + data rows


def test_generate_markdown_excludes_identical_by_default(temp_dir: Path):
    """Test that identical files are excluded from markdown details by default."""
    entries = [
        DiffEntry(path=Path("same.txt"), status="identical", source_hash="abc", dest_hash="abc"),
        DiffEntry(path=Path("diff.txt"), status="changed", source_hash="aaa", dest_hash="bbb"),
    ]
    result = ComparisonResult(entries=entries, summary={
        "total": 2,
        "identical": 1,
        "changed": 1,
    })

    md = generate_markdown(result, include_identical=False, hash_files=True)

    assert "`diff.txt`" in md
    assert "`same.txt`" not in md


def test_generate_markdown_includes_identical_when_requested(temp_dir: Path):
    """Test that identical files are included when include_identical=True."""
    entries = [
        DiffEntry(path=Path("same.txt"), status="identical", source_hash="abc", dest_hash="abc", source_size=10, dest_size=10),
        DiffEntry(path=Path("diff.txt"), status="changed", source_hash="aaa", dest_hash="bbb"),
    ]
    result = ComparisonResult(entries=entries, summary={
        "total": 2,
        "identical": 1,
        "changed": 1,
    })

    md = generate_markdown(result, include_identical=True, hash_files=True)

    assert "`diff.txt`" in md
    assert "`same.txt`" in md
    assert "Identical" in md