"""
Sensitive file filtering for WP Migration Integrity Verifier.

Provides patterns to exclude sensitive files from analysis and reports.
"""

from pathlib import Path
from typing import Iterable


SENSITIVE_PATTERNS = [
    ".env",
    ".env.*",
    "wp-config.php",
    "wp-config*.php",
    "*.pem",
    "*.key",
    "*.crt",
    "*.csr",
    "*.pfx",
    "*.p12",
    "id_rsa*",
    "id_ed25519*",
    "*.secret",
    "*.secrets",
    "secrets.*",
    "config.secret.*",
    ".htaccess",
    ".htpasswd",
    "auth.json",
    "composer.lock",
    "*.sql",
    "*.sql.gz",
    "*.sql.bz2",
    "*.sql.xz",
    "backup-*",
    "backup.*",
    "*.bak",
    "*.backup",
    "*.log",
    "debug.log",
    "error_log",
    "php_errors.log",
    "*.swp",
    "*.swo",
    "*~",
    ".DS_Store",
    "Thumbs.db",
]


def is_sensitive(path: Path, root: Path) -> bool:
    """
    Check if a file path matches any sensitive pattern.

    Args:
        path: Absolute path to the file.
        root: Root directory of the scan (for relative matching).

    Returns:
        True if the file should be excluded, False otherwise.
    """
    try:
        rel_path = path.relative_to(root)
    except ValueError:
        return True

    rel_str = str(rel_path)
    name = path.name

    for pattern in SENSITIVE_PATTERNS:
        if _match_pattern(name, pattern) or _match_pattern(rel_str, pattern):
            return True

    return False


def _match_pattern(text: str, pattern: str) -> bool:
    """Match text against a glob-style pattern."""
    import fnmatch
    return fnmatch.fnmatch(text, pattern) or fnmatch.fnmatch(text.lower(), pattern.lower())


def filter_sensitive(paths: Iterable[Path], root: Path) -> list[Path]:
    """
    Filter out sensitive files from an iterable of paths.

    Args:
        paths: Iterable of absolute file paths.
        root: Root directory of the scan.

    Returns:
        List of non-sensitive paths.
    """
    return [p for p in paths if not is_sensitive(p, root)]