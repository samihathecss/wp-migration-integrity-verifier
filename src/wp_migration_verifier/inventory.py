"""
File inventory collection for WP Migration Integrity Verifier.

Walks directories and collects file metadata without following symlinks
outside the selected root directory.
"""

from dataclasses import dataclass
from pathlib import Path
from typing import Iterator
import os
import stat

from .filters import is_sensitive


@dataclass(frozen=True, slots=True)
class FileEntry:
    """Represents a single file in the inventory."""
    path: Path
    size: int
    mtime: float
    is_symlink: bool
    error: str | None = None
    relative_path: Path | None = None
    skipped: bool = False


def collect_inventory(root: Path) -> Iterator[FileEntry]:
    """
    Walk a directory tree and yield FileEntry for each regular file.

    Does not follow symlinks that point outside the root directory.
    Skips unreadable files and directories, recording errors.

    Args:
        root: Root directory to scan (must be absolute).

    Yields:
        FileEntry objects for each file found.
    """
    root = root.resolve()
    if not root.is_dir():
        raise NotADirectoryError(f"Root path is not a directory: {root}")

    for dirpath, dirnames, filenames in os.walk(root, followlinks=False):
        current_dir = Path(dirpath)

        # Filter out symlinks to directories that escape the root
        dirnames[:] = [
            d for d in dirnames
            if not _is_escaping_symlink(current_dir / d, root)
        ]

        for filename in filenames:
            file_path = current_dir / filename

            # Skip sensitive files early
            if is_sensitive(file_path, root):
                yield FileEntry(
                    path=file_path,
                    size=0,
                    mtime=0.0,
                    is_symlink=False,
                    error=None,
                    skipped=True
                )
                continue

            try:
                stat_result = file_path.lstat()
            except (OSError, PermissionError) as e:
                yield FileEntry(
                    path=file_path,
                    size=0,
                    mtime=0.0,
                    is_symlink=False,
                    error=f"unreadable: {e}"
                )
                continue

            is_symlink = stat.S_ISLNK(stat_result.st_mode)

            # Skip symlinks that escape the root
            if is_symlink and _is_escaping_symlink(file_path, root):
                yield FileEntry(
                    path=file_path,
                    size=0,
                    mtime=0.0,
                    is_symlink=True,
                    error="excluded: symlink escapes root"
                )
                continue

            yield FileEntry(
                path=file_path,
                size=stat_result.st_size,
                mtime=stat_result.st_mtime,
                is_symlink=is_symlink,
                error=None
            )


def _is_escaping_symlink(path: Path, root: Path) -> bool:
    """
    Check if a symlink points outside the root directory.

    Args:
        path: Path to the symlink.
        root: Root directory boundary.

    Returns:
        True if the symlink target escapes the root, False otherwise.
    """
    try:
        target = path.resolve()
        return not _is_subpath(target, root)
    except (OSError, RuntimeError):
        # If we can't resolve, treat as escaping for safety
        return True


def _is_subpath(path: Path, root: Path) -> bool:
    """Check if path is within root directory."""
    try:
        path.relative_to(root)
        return True
    except ValueError:
        return False


def build_inventory_dict(root: Path) -> dict[Path, FileEntry]:
    """
    Build a dictionary mapping relative paths to FileEntry objects.

    Args:
        root: Root directory to scan.

    Returns:
        Dictionary mapping relative paths to FileEntry.
    """
    inventory = {}
    for entry in collect_inventory(root):
        rel_path = entry.path.relative_to(root)
        # Create a new entry with relative_path set
        new_entry = FileEntry(
            path=entry.path,
            size=entry.size,
            mtime=entry.mtime,
            is_symlink=entry.is_symlink,
            error=entry.error,
            relative_path=rel_path,
            skipped=entry.skipped
        )
        inventory[rel_path] = new_entry
    return inventory