"""
WP Migration Integrity Verifier

A tool to verify WordPress migrations by comparing file inventories
and SHA-256 hashes between source and destination directories.
"""

__version__ = "0.1.0"
__author__ = "WP Migration Integrity Verifier Contributors"

from .cli import main
from .compare import compare_inventories, ComparisonResult, DiffEntry
from .filters import is_sensitive, filter_sensitive
from .hashing import hash_file, hash_file_if_needed
from .inventory import collect_inventory, build_inventory_dict, FileEntry
from .report import generate_report, write_report

__all__ = [
    "main",
    "compare_inventories",
    "ComparisonResult",
    "DiffEntry",
    "is_sensitive",
    "filter_sensitive",
    "hash_file",
    "hash_file_if_needed",
    "collect_inventory",
    "build_inventory_dict",
    "FileEntry",
    "generate_report",
    "write_report",
]