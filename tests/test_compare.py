"""
Tests for compare module.
"""

from pathlib import Path
import pytest

from wp_migration_verifier.compare import compare_inventories, ComparisonResult, DiffEntry


def test_compare_identical_dirs(identical_dirs):
    """Test comparison of identical directories."""
    source, dest = identical_dirs
    result = compare_inventories(source, dest, hash_files=True)

    assert isinstance(result, ComparisonResult)
    assert result.summary["total"] > 0
    assert result.summary["identical"] == result.summary["total"]
    assert result.summary["missing"] == 0
    assert result.summary["added"] == 0
    assert result.summary["changed"] == 0
    assert result.summary["error"] == 0

    # All entries should be identical
    for entry in result.entries:
        assert entry.status == "identical"
        assert entry.source_hash == entry.dest_hash
        assert entry.source_hash is not None


def test_compare_identical_dirs_no_hash(identical_dirs):
    """Test comparison without hashing (size only)."""
    source, dest = identical_dirs
    result = compare_inventories(source, dest, hash_files=False)

    assert result.summary["size-matched"] == result.summary["total"]
    for entry in result.entries:
        assert entry.status == "size-matched"
        assert entry.source_hash is None
        assert entry.dest_hash is None


def test_compare_same_size_different_content_no_hash(temp_dir: Path):
    """Test same-size files with different content are 'size-matched' when hashing disabled."""
    source = temp_dir / "source"
    dest = temp_dir / "dest"
    source.mkdir()
    dest.mkdir()

    # Same size (10 bytes), different content
    (source / "file.txt").write_bytes(b"HelloWorld")   # 10 bytes
    (dest / "file.txt").write_bytes(b"GoodbyWorl")    # 10 bytes, different content

    result = compare_inventories(source, dest, hash_files=False)

    assert result.summary["size-matched"] == 1
    assert result.summary["identical"] == 0
    assert result.summary["changed"] == 0
    assert result.entries[0].status == "size-matched"
    assert result.entries[0].source_hash is None
    assert result.entries[0].dest_hash is None


def test_compare_same_size_different_content_with_hash(temp_dir: Path):
    """Test same-size files with different content are 'changed' when hashing enabled."""
    source = temp_dir / "source"
    dest = temp_dir / "dest"
    source.mkdir()
    dest.mkdir()

    # Same size (10 bytes), different content
    (source / "file.txt").write_bytes(b"HelloWorld")
    (dest / "file.txt").write_bytes(b"GoodbyWorl")

    result = compare_inventories(source, dest, hash_files=True)

    assert result.summary["changed"] == 1
    assert result.summary["identical"] == 0
    assert result.summary["size-matched"] == 0
    assert result.entries[0].status == "changed"
    assert result.entries[0].source_hash != result.entries[0].dest_hash


def test_compare_different_dirs(different_dirs):
    """Test comparison with missing, added, and changed files."""
    source, dest = different_dirs
    result = compare_inventories(source, dest, hash_files=True)

    # Should have: 1 missing, 2 added, 1 changed, 1 identical
    assert result.summary["missing"] == 1  # only-in-source.txt
    assert result.summary["added"] == 2    # only-in-dest.txt, extra.php
    assert result.summary["changed"] == 1  # style.css
    assert result.summary["identical"] == 1  # index.php
    assert result.summary["error"] == 0

    # Check specific entries
    missing = result.missing
    assert len(missing) == 1
    assert missing[0].path.name == "only-in-source.txt"

    added = result.added
    assert len(added) == 2
    added_names = {e.path.name for e in added}
    assert added_names == {"only-in-dest.txt", "extra.php"}

    changed = result.changed
    assert len(changed) == 1
    assert changed[0].path.name == "style.css"
    assert changed[0].source_hash != changed[0].dest_hash


def test_compare_sensitive_files_excluded(sensitive_files_dir):
    """Test that sensitive files are excluded from comparison."""
    source, dest = sensitive_files_dir
    result = compare_inventories(source, dest, hash_files=True)

    # normal.txt should be identical, sensitive files should be skipped
    assert result.summary["identical"] == 1
    assert result.summary["skipped"] == 4  # wp-config.php, .env, private.key, debug.log
    assert result.summary["missing"] == 0
    assert result.summary["added"] == 0
    assert result.summary["changed"] == 0
    assert result.summary["error"] == 0

    # Check that normal.txt is the only non-skipped entry
    non_skipped = [e for e in result.entries if e.status != "skipped"]
    assert len(non_skipped) == 1
    assert non_skipped[0].path.name == "normal.txt"
    assert non_skipped[0].status == "identical"


def test_compare_symlinks(symlink_dirs):
    """Test comparison with symlinks."""
    source, dest = symlink_dirs
    result = compare_inventories(source, dest, hash_files=True)

    # Should have real-file.txt, target.txt, link-to-target.txt (internal)
    # link-to-external.txt should be excluded
    assert result.summary["error"] == 0

    paths = {e.path.name for e in result.entries}
    assert "real-file.txt" in paths
    assert "target.txt" in paths
    assert "link-to-target.txt" in paths
    assert "link-to-external.txt" not in paths


def test_compare_unreadable_files(unreadable_file_dir):
    """Test comparison with unreadable files."""
    source, dest = unreadable_file_dir
    result = compare_inventories(source, dest, hash_files=True)

    # readable.txt should be identical
    # unreadable.txt should be error in source
    assert result.summary["identical"] == 1
    assert result.summary["error"] == 1

    error_entries = result.errors
    assert len(error_entries) == 1
    assert error_entries[0].path.name == "unreadable.txt"


def test_compare_empty_dirs(temp_dir: Path):
    """Test comparison of empty directories."""
    source = temp_dir / "source"
    dest = temp_dir / "dest"
    source.mkdir()
    dest.mkdir()

    result = compare_inventories(source, dest)
    assert result.summary["total"] == 0
    assert len(result.entries) == 0


def test_compare_source_empty_dest_not(temp_dir: Path):
    """Test comparison when source is empty but dest has files."""
    source = temp_dir / "source"
    dest = temp_dir / "dest"
    source.mkdir()
    dest.mkdir()
    (dest / "file.txt").write_text("content")

    result = compare_inventories(source, dest)
    assert result.summary["added"] == 1
    assert result.summary["missing"] == 0
    assert result.entries[0].status == "added"
    assert result.entries[0].path.name == "file.txt"


def test_compare_dest_empty_source_not(temp_dir: Path):
    """Test comparison when dest is empty but source has files."""
    source = temp_dir / "source"
    dest = temp_dir / "dest"
    source.mkdir()
    dest.mkdir()
    (source / "file.txt").write_text("content")

    result = compare_inventories(source, dest)
    assert result.summary["missing"] == 1
    assert result.summary["added"] == 0
    assert result.entries[0].status == "missing"
    assert result.entries[0].path.name == "file.txt"


def test_diff_entry_attributes():
    """Test DiffEntry dataclass."""
    entry = DiffEntry(
        path=Path("test.txt"),
        status="changed",
        source_hash="abc",
        dest_hash="def",
        source_size=100,
        dest_size=200,
        error=None
    )
    assert entry.path == Path("test.txt")
    assert entry.status == "changed"
    assert entry.source_hash == "abc"
    assert entry.dest_hash == "def"
    assert entry.source_size == 100
    assert entry.dest_size == 200


def test_comparison_result_properties(different_dirs):
    """Test ComparisonResult property filters."""
    source, dest = different_dirs
    result = compare_inventories(source, dest)

    assert len(result.missing) == result.summary["missing"]
    assert len(result.added) == result.summary["added"]
    assert len(result.changed) == result.summary["changed"]
    assert len(result.identical) == result.summary["identical"]
    assert len(result.errors) == result.summary["error"]