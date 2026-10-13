# WP Migration Integrity Verifier

A Python tool to verify WordPress migrations by comparing file inventories and SHA-256 hashes between source and destination directories.

## Features

- **File Inventory Comparison**: Compares file lists between source and destination
- **SHA-256 Hash Verification**: Streaming hash computation for large files
- **Sensitive File Exclusion**: Automatically excludes `.env`, `wp-config.php`, keys, certificates, SQL dumps, logs, and more
- **Symlink Safety**: Does not follow symlinks that escape the scan root
- **Error Handling**: Reports unreadable files and other errors without crashing
- **JSON Reports**: Structured output with summary and detailed differences
- **Offline Operation**: No network access required
- **Read-Only**: Never modifies, deletes, or executes analyzed files

## Installation

```bash
# Clone or download the project
cd wp-migration-verifier

# Install in development mode
pip install -e ".[dev]"
```

Requires Python 3.9+.

## Usage

```bash
# Basic comparison with hash verification
wp-migration-verify /path/to/source /path/to/destination -o report.json

# Compare by size only (faster, less accurate)
wp-migration-verify /path/to/source /path/to/destination --no-hash

# Include identical files in report details
wp-migration-verify /path/to/source /path/to/destination --include-identical

# Quiet mode (only errors)
wp-migration-verify /path/to/source /path/to/destination -q
```

### Exit Codes

- `0`: No differences found (identical)
- `1`: Differences found (missing, added, changed, or errors)
- `2`: Usage error or fatal exception

## Report Format

The tool generates a JSON report with this structure:

```json
{
  "summary": {
    "total": 150,
    "identical": 145,
    "missing": 2,
    "added": 1,
    "changed": 2,
    "error": 0,
    "skipped": 0
  },
  "details": [
    {
      "path": "wp-content/uploads/image.jpg",
      "status": "identical",
      "source_hash": "a1b2c3...",
      "dest_hash": "a1b2c3...",
      "source_size": 102400,
      "dest_size": 102400
    },
    {
      "path": "wp-config.php",
      "status": "missing",
      "source_hash": "d4e5f6...",
      "source_size": 3200
    },
    {
      "path": "new-plugin.php",
      "status": "added",
      "dest_hash": "f7g8h9...",
      "dest_size": 5120
    },
    {
      "path": "style.css",
      "status": "changed",
      "source_hash": "aaa...",
      "dest_hash": "bbb...",
      "source_size": 2048,
      "dest_size": 2048
    },
    {
      "path": "restricted.txt",
      "status": "error",
      "error": "unreadable: permission denied"
    }
  ],
  "note": "File comparison only. Does not verify database, configuration, or runtime behavior."
}
```

### Status Values

| Status | Meaning |
|--------|---------|
| `identical` | File exists in both with same size and hash |
| `missing` | File exists in source but not destination |
| `added` | File exists in destination but not source |
| `changed` | File exists in both but hash differs (or size differs) |
| `skipped` | File was excluded (sensitive pattern) |
| `error` | File could not be read or hashed |

## Excluded Files

The following patterns are automatically excluded from analysis and reports:

- **Configuration**: `wp-config.php`, `.env`, `.env.*`, `config.secret.*`
- **Keys/Certificates**: `*.pem`, `*.key`, `*.crt`, `*.csr`, `*.pfx`, `*.p12`, `id_rsa*`, `id_ed25519*`
- **Secrets**: `*.secret`, `*.secrets`, `secrets.*`, `auth.json`
- **Database**: `*.sql`, `*.sql.gz`, `*.sql.bz2`, `*.sql.xz`
- **Backups**: `backup-*`, `*.bak`, `*.backup`
- **Logs**: `*.log`, `debug.log`, `error_log`, `php_errors.log`
- **Web Server**: `.htaccess`, `.htpasswd`
- **System**: `.DS_Store`, `Thumbs.db`, `*.swp`, `*.swo`, `*~`

## Limitations

⚠️ **This tool only compares files.** It does **not** verify:

- Database content, structure, or integrity
- WordPress configuration correctness
- Plugin/theme functionality
- Runtime behavior or site accessibility
- File permissions or ownership
- Symbolic link targets (only validates they don't escape root)
- Malware or code integrity beyond hash matching

A clean file comparison **does not guarantee** a successful migration. Always perform functional testing.

## Development

```bash
# Install dev dependencies
pip install -e ".[dev]"

# Run tests
pytest

# Run tests with coverage
pytest --cov=wp_migration_verifier

# Type checking (if mypy configured)
mypy src/wp_migration_verifier
```

## Project Structure

```
src/wp_migration_verifier/
├── __init__.py       # Package exports
├── cli.py            # Command-line interface
├── compare.py        # Comparison logic
├── filters.py        # Sensitive file patterns
├── hashing.py        # Streaming SHA-256
├── inventory.py      # File inventory collection
└── report.py         # JSON report generation

tests/
├── conftest.py       # Pytest fixtures
├── test_inventory.py
├── test_hashing.py
├── test_compare.py
├── test_filters.py
├── test_report.py
└── test_cli.py
```

## License

MIT License - see LICENSE file for details.