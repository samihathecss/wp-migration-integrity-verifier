"""
Tests for hashing module.
"""

import sys
from pathlib import Path
import hashlib
import pytest

from wp_migration_verifier.hashing import hash_file, hash_file_if_needed


IS_WINDOWS = sys.platform == "win32"


def test_hash_file_basic(temp_dir: Path):
    """Test basic file hashing."""
    file_path = temp_dir / "test.txt"
    file_path.write_bytes(b"Hello, World!")

    hash_val, error = hash_file(file_path)
    assert error is None
    assert hash_val == hashlib.sha256(b"Hello, World!").hexdigest()


def test_hash_file_empty(temp_dir: Path):
    """Test hashing empty file."""
    file_path = temp_dir / "empty.txt"
    file_path.write_bytes(b"")

    hash_val, error = hash_file(file_path)
    assert error is None
    assert hash_val == hashlib.sha256(b"").hexdigest()


def test_hash_file_large(temp_dir: Path):
    """Test hashing large file (streaming)."""
    file_path = temp_dir / "large.bin"
    # Write 5MB of data
    data = b"x" * (5 * 1024 * 1024)
    file_path.write_bytes(data)

    hash_val, error = hash_file(file_path)
    assert error is None
    assert hash_val == hashlib.sha256(data).hexdigest()


def test_hash_file_unreadable(temp_dir: Path):
    """Test hashing unreadable file returns error (skipped on Windows)."""
    if IS_WINDOWS:
        pytest.skip("chmod 0o000 doesn't make files unreadable on Windows")
    file_path = temp_dir / "unreadable.txt"
    file_path.write_bytes(b"secret")
    try:
        file_path.chmod(0o000)
    except (OSError, NotImplementedError):
        pytest.skip("Cannot create unreadable file on this platform")

    hash_val, error = hash_file(file_path)
    assert hash_val is None
    assert error is not None
    assert "hash failed" in error


def test_hash_file_nonexistent(temp_dir: Path):
    """Test hashing nonexistent file returns error."""
    file_path = temp_dir / "nonexistent.txt"

    hash_val, error = hash_file(file_path)
    assert hash_val is None
    assert error is not None


def test_hash_file_if_needed_empty(temp_dir: Path):
    """Test hash_file_if_needed for empty file."""
    file_path = temp_dir / "empty.txt"
    file_path.write_bytes(b"")

    hash_val, error = hash_file_if_needed(file_path, 0)
    assert error is None
    assert hash_val == hashlib.sha256(b"").hexdigest()


def test_hash_file_if_needed_nonempty(temp_dir: Path):
    """Test hash_file_if_needed for non-empty file."""
    file_path = temp_dir / "test.txt"
    file_path.write_bytes(b"content")

    hash_val, error = hash_file_if_needed(file_path, 7)
    assert error is None
    assert hash_val == hashlib.sha256(b"content").hexdigest()