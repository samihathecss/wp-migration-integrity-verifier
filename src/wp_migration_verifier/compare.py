"""
Comparison logic for WP Migration Integrity Verifier.

Compares source and destination inventories and hashes.
"""

from dataclasses import dataclass
from pathlib import Path
from typing import Optional

from .inventory import FileEntry, build_inventory_dict
from .hashing import hash_file_if_needed


@dataclass(frozen=True, slots=True)
class DiffEntry:
    """Represents a difference between source and destination."""
    path: Path
    status: str  # "missing", "added", "changed", "identical", "skipped", "error"
    source_hash: Optional[str] = None
    dest_hash: Optional[str] = None
    source_size: int = 0
    dest_size: int = 0
    error: Optional[str] = None


@dataclass(frozen=True, slots=True)
class ComparisonResult:
    """Complete comparison result with summary statistics."""
    entries: list[DiffEntry]
    summary: dict[str, int]

    @property
    def missing(self) -> list[DiffEntry]:
        return [e for e in self.entries if e.status == "missing"]

    @property
    def added(self) -> list[DiffEntry]:
        return [e for e in self.entries if e.status == "added"]

    @property
    def changed(self) -> list[DiffEntry]:
        return [e for e in self.entries if e.status == "changed"]

    @property
    def identical(self) -> list[DiffEntry]:
        return [e for e in self.entries if e.status == "identical"]

    @property
    def skipped(self) -> list[DiffEntry]:
        return [e for e in self.entries if e.status == "skipped"]

    @property
    def errors(self) -> list[DiffEntry]:
        return [e for e in self.entries if e.status == "error"]


def compare_inventories(
    source_root: Path,
    dest_root: Path,
    *,
    hash_files: bool = True,
    chunk_size: int = 1024 * 1024
) -> ComparisonResult:
    """
    Compare source and destination directories.

    Args:
        source_root: Source directory path.
        dest_root: Destination directory path.
        hash_files: Whether to compute and compare SHA-256 hashes.
        chunk_size: Chunk size for streaming hash.

    Returns:
        ComparisonResult with all differences and summary.
    """
    source_inv = build_inventory_dict(source_root)
    dest_inv = build_inventory_dict(dest_root)

    all_paths = set(source_inv.keys()) | set(dest_inv.keys())
    entries = []

    for rel_path in sorted(all_paths):
        src_entry = source_inv.get(rel_path)
        dst_entry = dest_inv.get(rel_path)

        if src_entry is None:
            # Added in destination
            if dst_entry and dst_entry.skipped:
                entries.append(DiffEntry(
                    path=rel_path,
                    status="skipped",
                ))
            else:
                entries.append(DiffEntry(
                    path=rel_path,
                    status="added",
                    dest_size=dst_entry.size if dst_entry else 0,
                    error=dst_entry.error if dst_entry else None
                ))
        elif dst_entry is None:
            # Missing in destination
            if src_entry and src_entry.skipped:
                entries.append(DiffEntry(
                    path=rel_path,
                    status="skipped",
                ))
            else:
                entries.append(DiffEntry(
                    path=rel_path,
                    status="missing",
                    source_size=src_entry.size,
                    source_hash=_get_hash(src_entry, source_root, hash_files, chunk_size),
                    error=src_entry.error
                ))
        else:
            # Both exist - compare
            if src_entry.skipped and dst_entry.skipped:
                # Both skipped (sensitive files) - count as skipped
                entries.append(DiffEntry(
                    path=rel_path,
                    status="skipped",
                ))
            elif src_entry.error or dst_entry.error:
                entries.append(DiffEntry(
                    path=rel_path,
                    status="error",
                    source_size=src_entry.size,
                    dest_size=dst_entry.size,
                    error=f"source: {src_entry.error}; dest: {dst_entry.error}"
                ))
            elif src_entry.size != dst_entry.size:
                entries.append(DiffEntry(
                    path=rel_path,
                    status="changed",
                    source_size=src_entry.size,
                    dest_size=dst_entry.size,
                    source_hash=_get_hash(src_entry, source_root, hash_files, chunk_size),
                    dest_hash=_get_hash(dst_entry, dest_root, hash_files, chunk_size)
                ))
            else:
                # Same size - check hash if enabled
                src_hash = _get_hash(src_entry, source_root, hash_files, chunk_size)
                dst_hash = _get_hash(dst_entry, dest_root, hash_files, chunk_size)

                if src_hash is not None and dst_hash is not None and src_hash != dst_hash:
                    entries.append(DiffEntry(
                        path=rel_path,
                        status="changed",
                        source_size=src_entry.size,
                        dest_size=dst_entry.size,
                        source_hash=src_hash,
                        dest_hash=dst_hash
                    ))
                else:
                    # Files match on hash (if computed) or only on size (if hashing disabled)
                    status = "identical" if hash_files else "size-matched"
                    entries.append(DiffEntry(
                        path=rel_path,
                        status=status,
                        source_size=src_entry.size,
                        dest_size=dst_entry.size,
                        source_hash=src_hash,
                        dest_hash=dst_hash
                    ))

    summary = _compute_summary(entries)
    return ComparisonResult(entries=entries, summary=summary)


def _get_hash(entry: FileEntry, root: Path, hash_files: bool, chunk_size: int) -> str | None:
    """Get hash for a file entry, computing if needed."""
    if not hash_files:
        return None
    if entry.error or entry.skipped:
        return None
    abs_path = root / entry.relative_path
    hash_val, err = hash_file_if_needed(abs_path, entry.size, chunk_size)
    if err:
        return None
    return hash_val


def _compute_summary(entries: list[DiffEntry]) -> dict[str, int]:
    """Compute summary statistics from entries."""
    counts = {
        "total": len(entries),
        "identical": 0,
        "missing": 0,
        "added": 0,
        "changed": 0,
        "skipped": 0,
        "error": 0,
        "size-matched": 0,
    }
    for e in entries:
        counts[e.status] = counts.get(e.status, 0) + 1
    return counts