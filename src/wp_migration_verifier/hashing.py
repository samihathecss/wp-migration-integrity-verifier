"""
Streaming SHA-256 hashing for WP Migration Integrity Verifier.

Handles large files efficiently by reading in chunks.
"""

import hashlib
from pathlib import Path
from typing import Optional

DEFAULT_CHUNK_SIZE = 1024 * 1024  # 1 MB


def hash_file(path: Path, chunk_size: int = DEFAULT_CHUNK_SIZE) -> tuple[str | None, str | None]:
    """
    Compute SHA-256 hash of a file using streaming.

    Args:
        path: Path to the file.
        chunk_size: Size of chunks to read (bytes).

    Returns:
        Tuple of (hex_hash, error_message). If successful, error_message is None.
        If failed, hex_hash is None and error_message describes the failure.
    """
    hasher = hashlib.sha256()
    try:
        with path.open("rb") as f:
            while chunk := f.read(chunk_size):
                hasher.update(chunk)
    except (OSError, PermissionError) as e:
        return None, f"hash failed: {e}"
    return hasher.hexdigest(), None


def hash_file_if_needed(path: Path, size: int, chunk_size: int = DEFAULT_CHUNK_SIZE) -> tuple[str | None, str | None]:
    """
    Compute SHA-256 hash only if file size > 0.

    Args:
        path: Path to the file.
        size: File size in bytes.
        chunk_size: Size of chunks to read (bytes).

    Returns:
        Tuple of (hex_hash, error_message). For empty files, returns
        the SHA-256 of empty content ("e3b0c44298fc1c149afbf4c8996fb924...") with no error.
    """
    if size == 0:
        return hashlib.sha256(b"").hexdigest(), None
    return hash_file(path, chunk_size)