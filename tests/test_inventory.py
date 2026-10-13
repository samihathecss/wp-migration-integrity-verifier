"""
Tests for inventory module.
"""

import sys
from pathlib import Path
import pytest

from wp_migration_verifier.inventory import collect_inventory, build_inventory_dict, FileEntry
from wp_migration_verifier.filters import is_sensitive


IS_WINDOWS = sys.platform == "win32"


def test_collect_inventory_basic(temp_dir: Path):
    """Test basic inventory collection."""
    src = temp_dir / "source"
    src.mkdir()
    (src / "file1.txt").write_text("content1")
    (src / "file2.txt").write_text("content2")
    (src / "subdir").mkdir()
    (src / "subdir" / "file3.txt").write_text("content3")

    entries = list(collect_inventory(src))
    assert len(entries) == 3

    paths = {e.path.relative_to(src) for e in entries}
    assert paths == {
        Path("file1.txt"),
        Path("file2.txt"),
        Path("subdir/file3.txt"),
    }


def test_collect_inventory_excludes_sensitive(temp_dir: Path):
    """Test that sensitive files are marked as skipped."""
    src = temp_dir / "source"
    src.mkdir()
    (src / "normal.txt").write_text("normal")
    (src / "wp-config.php").write_text("<?php secret")
    (src / ".env").write_text("SECRET=value")
    (src / "private.key").write_text("key")

    entries = list(collect_inventory(src))

    normal_entries = [e for e in entries if not e.skipped]
    skipped_entries = [e for e in entries if e.skipped]

    assert len(normal_entries) == 1
    assert normal_entries[0].path.name == "normal.txt"
    assert len(skipped_entries) == 3
    skipped_names = {e.path.name for e in skipped_entries}
    assert skipped_names == {"wp-config.php", ".env", "private.key"}


def test_collect_inventory_symlink_internal(temp_dir: Path):
    """Test internal symlinks are followed (skipped on Windows)."""
    if IS_WINDOWS:
        pytest.skip("Symlinks require admin privileges on Windows")
    src = temp_dir / "source"
    src.mkdir()
    (src / "real.txt").write_text("real content")
    (src / "link.txt").symlink_to("real.txt")

    entries = list(collect_inventory(src))
    assert len(entries) == 2

    # Both should be present
    names = {e.path.name for e in entries}
    assert names == {"real.txt", "link.txt"}


def test_collect_inventory_symlink_external_excluded(temp_dir: Path):
    """Test external symlinks are excluded (skipped on Windows)."""
    if IS_WINDOWS:
        pytest.skip("Symlinks require admin privileges on Windows")
    src = temp_dir / "source"
    src.mkdir()
    external = temp_dir / "external.txt"
    external.write_text("external")

    (src / "internal.txt").write_text("internal")
    (src / "external-link.txt").symlink_to(external)

    entries = list(collect_inventory(src))

    # Should only have internal.txt, external-link.txt should be excluded
    included = [e for e in entries if e.error is None]
    excluded = [e for e in entries if e.error and "escapes" in e.error]

    assert len(included) == 1
    assert included[0].path.name == "internal.txt"
    assert len(excluded) == 1
    assert excluded[0].path.name == "external-link.txt"


def test_collect_inventory_unreadable_file(temp_dir: Path):
    """Test unreadable files are recorded with error (skipped on Windows)."""
    if IS_WINDOWS:
        pytest.skip("chmod 0o000 doesn't make files unreadable on Windows")
    src = temp_dir / "source"
    src.mkdir()
    (src / "readable.txt").write_text("readable")

    unreadable = src / "unreadable.txt"
    unreadable.write_text("secret")
    try:
        unreadable.chmod(0o000)
    except (OSError, NotImplementedError):
        pytest.skip("Cannot create unreadable file on this platform")

    entries = list(collect_inventory(src))

    readable_entries = [e for e in entries if e.error is None]
    error_entries = [e for e in entries if e.error and "unreadable" in e.error]

    assert len(readable_entries) == 1
    assert len(error_entries) == 1


def test_build_inventory_dict(temp_dir: Path):
    """Test building inventory dictionary with relative paths."""
    src = temp_dir / "source"
    src.mkdir()
    (src / "file1.txt").write_text("content1")
    (src / "subdir").mkdir()
    (src / "subdir" / "file2.txt").write_text("content2")

    inv = build_inventory_dict(src)

    assert len(inv) == 2
    assert Path("file1.txt") in inv
    assert Path("subdir/file2.txt") in inv

    # Check relative_path is set
    for entry in inv.values():
        assert entry.relative_path == entry.path.relative_to(src)


def test_file_entry_attributes():
    """Test FileEntry dataclass attributes."""
    entry = FileEntry(
        path=Path("/root/file.txt"),
        size=100,
        mtime=1234567890.0,
        is_symlink=False,
        error=None
    )
    assert entry.size == 100
    assert entry.mtime == 1234567890.0
    assert entry.is_symlink is False
    assert entry.error is None
    assert entry.skipped is False
    assert entry.relative_path is None