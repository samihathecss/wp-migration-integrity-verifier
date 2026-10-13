"""
Tests for filters module.
"""

from pathlib import Path
import pytest

from wp_migration_verifier.filters import is_sensitive, filter_sensitive, SENSITIVE_PATTERNS


def test_is_sensitive_wp_config():
    """Test wp-config.php is detected as sensitive."""
    root = Path("/site")
    assert is_sensitive(root / "wp-config.php", root) is True
    assert is_sensitive(root / "wp-config-sample.php", root) is True
    assert is_sensitive(root / "wp-config-production.php", root) is True


def test_is_sensitive_env_files():
    """Test .env files are detected as sensitive."""
    root = Path("/site")
    assert is_sensitive(root / ".env", root) is True
    assert is_sensitive(root / ".env.production", root) is True
    assert is_sensitive(root / ".env.local", root) is True


def test_is_sensitive_keys_and_certs():
    """Test key/cert files are detected as sensitive."""
    root = Path("/site")
    assert is_sensitive(root / "private.key", root) is True
    assert is_sensitive(root / "cert.pem", root) is True
    assert is_sensitive(root / "cert.crt", root) is True
    assert is_sensitive(root / "cert.csr", root) is True
    assert is_sensitive(root / "bundle.pfx", root) is True
    assert is_sensitive(root / "bundle.p12", root) is True


def test_is_sensitive_ssh_keys():
    """Test SSH keys are detected as sensitive."""
    root = Path("/site")
    assert is_sensitive(root / "id_rsa", root) is True
    assert is_sensitive(root / "id_rsa.pub", root) is True
    assert is_sensitive(root / "id_ed25519", root) is True
    assert is_sensitive(root / "id_ed25519.pub", root) is True


def test_is_sensitive_secrets():
    """Test secret files are detected as sensitive."""
    root = Path("/site")
    assert is_sensitive(root / "secrets.json", root) is True
    assert is_sensitive(root / "config.secret.yaml", root) is True
    assert is_sensitive(root / "api.secret", root) is True


def test_is_sensitive_htaccess():
    """Test .htaccess and .htpasswd are detected as sensitive."""
    root = Path("/site")
    assert is_sensitive(root / ".htaccess", root) is True
    assert is_sensitive(root / ".htpasswd", root) is True


def test_is_sensitive_sql_dumps():
    """Test SQL dump files are detected as sensitive."""
    root = Path("/site")
    assert is_sensitive(root / "database.sql", root) is True
    assert is_sensitive(root / "dump.sql.gz", root) is True
    assert is_sensitive(root / "backup.sql.bz2", root) is True
    assert is_sensitive(root / "export.sql.xz", root) is True


def test_is_sensitive_backups():
    """Test backup files are detected as sensitive."""
    root = Path("/site")
    assert is_sensitive(root / "backup-2024.sql", root) is True
    assert is_sensitive(root / "site.bak", root) is True
    assert is_sensitive(root / "backup.zip", root) is True


def test_is_sensitive_logs():
    """Test log files are detected as sensitive."""
    root = Path("/site")
    assert is_sensitive(root / "debug.log", root) is True
    assert is_sensitive(root / "error_log", root) is True
    assert is_sensitive(root / "php_errors.log", root) is True
    assert is_sensitive(root / "access.log", root) is True


def test_is_sensitive_temp_files():
    """Test temp/editor files are detected as sensitive."""
    root = Path("/site")
    assert is_sensitive(root / ".DS_Store", root) is True
    assert is_sensitive(root / "Thumbs.db", root) is True
    assert is_sensitive(root / "file.swp", root) is True
    assert is_sensitive(root / "file~", root) is True


def test_is_sensitive_normal_files():
    """Test normal files are NOT detected as sensitive."""
    root = Path("/site")
    assert is_sensitive(root / "index.php", root) is False
    assert is_sensitive(root / "style.css", root) is False
    assert is_sensitive(root / "script.js", root) is False
    assert is_sensitive(root / "image.png", root) is False
    assert is_sensitive(root / "readme.txt", root) is False
    assert is_sensitive(root / "wp-content/style.css", root) is False
    assert is_sensitive(root / "wp-includes/version.php", root) is False


def test_is_sensitive_case_insensitive():
    """Test matching is case-insensitive."""
    root = Path("/site")
    assert is_sensitive(root / "WP-CONFIG.PHP", root) is True
    assert is_sensitive(root / ".ENV", root) is True
    assert is_sensitive(root / "PRIVATE.KEY", root) is True


def test_is_sensitive_subdirectory():
    """Test sensitive files in subdirectories are detected."""
    root = Path("/site")
    assert is_sensitive(root / "wp-content" / "debug.log", root) is True
    assert is_sensitive(root / "wp-admin" / ".htaccess", root) is True
    assert is_sensitive(root / "config" / ".env", root) is True


def test_filter_sensitive():
    """Test filter_sensitive removes sensitive files."""
    root = Path("/site")
    paths = [
        root / "index.php",
        root / "wp-config.php",
        root / ".env",
        root / "style.css",
        root / "private.key",
    ]

    filtered = filter_sensitive(paths, root)
    assert len(filtered) == 2
    assert filtered[0].name == "index.php"
    assert filtered[1].name == "style.css"


def test_all_patterns_are_strings():
    """Ensure all patterns are strings."""
    for pattern in SENSITIVE_PATTERNS:
        assert isinstance(pattern, str)
        assert len(pattern) > 0