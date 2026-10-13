"""
Pytest fixtures and configuration for WP Migration Integrity Verifier tests.
"""

import tempfile
import sys
from pathlib import Path
from typing import Generator
import pytest
import os


IS_WINDOWS = sys.platform == "win32"


@pytest.fixture
def temp_dir() -> Generator[Path, None, None]:
    """Create a temporary directory that is cleaned up after the test."""
    with tempfile.TemporaryDirectory() as tmp:
        yield Path(tmp)


@pytest.fixture
def source_dir(temp_dir: Path) -> Path:
    """Create a source directory with test files."""
    src = temp_dir / "source"
    src.mkdir()
    return src


@pytest.fixture
def dest_dir(temp_dir: Path) -> Path:
    """Create a destination directory."""
    dst = temp_dir / "dest"
    dst.mkdir()
    return dst


def create_file(path: Path, content: bytes = b"") -> None:
    """Create a file with given content, creating parent directories as needed."""
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(content)


def create_symlink(link_path: Path, target: Path) -> None:
    """Create a symlink, skipping on platforms without support."""
    if IS_WINDOWS:
        pytest.skip("Symlinks not supported on this platform without admin privileges")
    try:
        link_path.symlink_to(target)
    except (OSError, NotImplementedError):
        pytest.skip("Symlinks not supported on this platform")


@pytest.fixture
def identical_dirs(source_dir: Path, dest_dir: Path) -> tuple[Path, Path]:
    """Create identical source and destination directories."""
    create_file(source_dir / "index.php", b"<?php echo 'Hello';")
    create_file(source_dir / "wp-content" / "style.css", b"body {}")
    create_file(source_dir / "wp-content" / "uploads" / "image.jpg", b"fake image data")
    create_file(source_dir / "readme.txt", b"WordPress")

    # Copy to destination
    import shutil
    shutil.copytree(source_dir, dest_dir, dirs_exist_ok=True)
    return source_dir, dest_dir


@pytest.fixture
def different_dirs(source_dir: Path, dest_dir: Path) -> tuple[Path, Path]:
    """Create source and destination with differences."""
    # Source files
    create_file(source_dir / "index.php", b"<?php echo 'Source';")
    create_file(source_dir / "wp-content" / "style.css", b"body { color: red; }")
    create_file(source_dir / "only-in-source.txt", b"Only in source")

    # Destination files
    create_file(dest_dir / "index.php", b"<?php echo 'Source';")  # Same as source
    create_file(dest_dir / "wp-content" / "style.css", b"body { color: blue; }")  # Different
    create_file(dest_dir / "only-in-dest.txt", b"Only in dest")
    create_file(dest_dir / "extra.php", b"<?php extra();")

    return source_dir, dest_dir


@pytest.fixture
def sensitive_files_dir(source_dir: Path, dest_dir: Path) -> tuple[Path, Path]:
    """Create directories with sensitive files that should be excluded."""
    create_file(source_dir / "wp-config.php", b"<?php define('DB_PASSWORD', 'secret');")
    create_file(source_dir / ".env", b"DB_PASSWORD=secret")
    create_file(source_dir / "private.key", b"-----BEGIN PRIVATE KEY-----")
    create_file(source_dir / "normal.txt", b"Normal file")
    create_file(source_dir / "wp-content" / "debug.log", b"Error log")

    create_file(dest_dir / "wp-config.php", b"<?php define('DB_PASSWORD', 'secret');")
    create_file(dest_dir / ".env", b"DB_PASSWORD=secret")
    create_file(dest_dir / "private.key", b"-----BEGIN PRIVATE KEY-----")
    create_file(dest_dir / "normal.txt", b"Normal file")

    return source_dir, dest_dir


@pytest.fixture
def symlink_dirs(source_dir: Path, dest_dir: Path) -> tuple[Path, Path]:
    """Create directories with symlinks (skipped on Windows)."""
    if IS_WINDOWS:
        pytest.skip("Symlink tests skipped on Windows")
    create_file(source_dir / "real-file.txt", b"Real content")
    create_file(source_dir / "subdir" / "target.txt", b"Target content")

    # Internal symlink (should be followed)
    create_symlink(source_dir / "link-to-target.txt", source_dir / "subdir" / "target.txt")

    # External symlink (should be excluded)
    external_target = source_dir.parent / "external.txt"
    create_file(external_target, b"External content")
    create_symlink(source_dir / "link-to-external.txt", external_target)

    # Copy to destination (without external symlink target)
    import shutil
    shutil.copytree(source_dir, dest_dir, dirs_exist_ok=True)

    # Remove the external target from destination scan root
    # (it's outside dest_dir anyway)
    return source_dir, dest_dir


@pytest.fixture
def unreadable_file_dir(source_dir: Path, dest_dir: Path) -> tuple[Path, Path]:
    """Create a directory with an unreadable file (where supported)."""
    if IS_WINDOWS:
        pytest.skip("Unreadable file test skipped on Windows")
    create_file(source_dir / "readable.txt", b"Readable")
    create_file(dest_dir / "readable.txt", b"Readable")

    # Try to create unreadable file (skip on Windows or if not supported)
    unreadable = source_dir / "unreadable.txt"
    create_file(unreadable, b"Secret")
    try:
        unreadable.chmod(0o000)
    except (OSError, NotImplementedError):
        pytest.skip("Cannot create unreadable file on this platform")

    return source_dir, dest_dir