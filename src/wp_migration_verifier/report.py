"""
JSON report generation for WP Migration Integrity Verifier.

Exports comparison results as structured JSON.
"""

import json
from dataclasses import asdict
from pathlib import Path
from typing import Any

from .compare import ComparisonResult, DiffEntry


def generate_report(
    result: ComparisonResult,
    *,
    include_identical: bool = False,
    hash_files: bool = True
) -> dict[str, Any]:
    """
    Generate a JSON-serializable report from comparison result.

    Args:
        result: ComparisonResult to report on.
        include_identical: Whether to include identical files in details.
        hash_files: Whether SHA-256 hashing was enabled.

    Returns:
        Dictionary ready for JSON serialization.
    """
    details = []
    for entry in result.entries:
        if entry.status == "identical" and not include_identical:
            continue
        details.append(_entry_to_dict(entry))

    summary = result.summary
    verification = _build_verification(summary, hash_files)

    return {
        "verification": verification,
        "summary": summary,
        "details": details,
        "note": "File comparison only. Does not verify database, configuration, or runtime behavior."
    }


def _build_verification(summary: dict[str, int], hash_files: bool) -> dict[str, Any]:
    """Build client-friendly verification summary."""
    missing = summary.get("missing", 0)
    added = summary.get("added", 0)
    changed = summary.get("changed", 0)
    skipped = summary.get("skipped", 0)
    errors = summary.get("error", 0)

    differences_found = (missing + added + changed) > 0
    review_required = differences_found or skipped > 0 or errors > 0

    return {
        "differences_found": differences_found,
        "files_missing": missing,
        "files_added": added,
        "files_changed": changed,
        "files_skipped": skipped,
        "hash_verified": hash_files,
        "review_required": review_required,
        "limitations": [
            "Database content not compared",
            "Configuration correctness not verified",
            "Runtime behavior not tested"
        ]
    }


def _entry_to_dict(entry: DiffEntry) -> dict[str, Any]:
    """Convert DiffEntry to dictionary."""
    d = {
        "path": str(entry.path),
        "status": entry.status,
    }
    if entry.source_size:
        d["source_size"] = entry.source_size
    if entry.dest_size:
        d["dest_size"] = entry.dest_size
    if entry.source_hash:
        d["source_hash"] = entry.source_hash
    if entry.dest_hash:
        d["dest_hash"] = entry.dest_hash
    if entry.error:
        d["error"] = entry.error
    return d


def _escape_md(text: str) -> str:
    """Escape text for safe use in Markdown table cells."""
    return text.replace("|", "\\|").replace("\n", " ").replace("\r", " ")


def _format_file_detail(entry: dict[str, Any]) -> str:
    """Format detail column for a file entry."""
    status = entry["status"]
    if status == "changed":
        src_sz = entry.get("source_size", 0)
        dst_sz = entry.get("dest_size", 0)
        return f"Hash differs (source: {src_sz} bytes, dest: {dst_sz} bytes)"
    elif status == "added":
        return f"{entry.get('dest_size', 0)} bytes (dest only)"
    elif status == "missing":
        return f"{entry.get('source_size', 0)} bytes (source only)"
    elif status == "skipped":
        return "Excluded from comparison (sensitive pattern)"
    elif status == "size-matched":
        return f"{entry.get('source_size', 0)} bytes (size matches, content not verified)"
    elif status == "identical":
        return f"{entry.get('source_size', 0)} bytes (hash verified)"
    elif status == "error":
        return entry.get("error", "Unknown error")
    return ""


def _status_label(status: str) -> str:
    """Return human-readable label for a status."""
    labels = {
        "identical": "Identical",
        "missing": "Missing",
        "added": "Added",
        "changed": "Changed",
        "skipped": "Skipped",
        "size-matched": "Size-matched",
        "error": "Error",
    }
    return labels.get(status, status.capitalize())


def generate_markdown(
    result: ComparisonResult,
    *,
    include_identical: bool = False,
    hash_files: bool = True
) -> str:
    """
    Generate a human-readable Markdown report from comparison result.

    Args:
        result: ComparisonResult to report on.
        include_identical: Whether to include identical files in details.
        hash_files: Whether SHA-256 hashing was enabled.

    Returns:
        Markdown-formatted string.
    """
    report = generate_report(result, include_identical=include_identical, hash_files=hash_files)
    v = report["verification"]
    s = report["summary"]

    # Overall status
    if v["review_required"]:
        if v["differences_found"]:
            status_line = "⚠️ **Review Required** — Differences found"
        else:
            status_line = "⚠️ **Review Required** — Sensitive files skipped"
    else:
        status_line = "✅ **No Differences Found**"

    lines = [
        "# WP Migration Integrity Report",
        f"**Overall Status:** {status_line}",
        "",
        "## Summary",
        "| Category | Count |",
        "|----------|-------|",
        f"| Missing in destination | {v['files_missing']} |",
        f"| Added in destination | {v['files_added']} |",
        f"| Changed (content differs) | {v['files_changed']} |",
        f"| Skipped | {v['files_skipped']} |",
        "",
        "## Verification",
        f"- **SHA-256 verification:** {'✅ Performed' if v['hash_verified'] else '❌ Skipped (size only)'}",
        f"- **Files compared:** {s['total']} total, {s.get('identical', 0)} identical, {s.get('size-matched', 0)} size-matched",
        "",
        "## Limitations",
        "This report **only compares files**. It does **not** verify:",
        *[f"- {lim}" for lim in v["limitations"]],
        "",
        "## Recommended Next Steps",
        "1. Review the missing, added, and changed files listed below",
        "2. Verify database migration separately",
        "3. Test site functionality in staging environment",
        "",
        "## Detailed Changes",
        "| File | Status | Details |",
        "|------|--------|---------|"
    ]

    if not report["details"]:
        lines.append("| — | — | No differences to report |")
    else:
        for entry in report["details"]:
            path = _escape_md(entry["path"])
            status_label = _status_label(entry["status"])
            detail = _escape_md(_format_file_detail(entry))
            lines.append(f"| `{path}` | {status_label} | {detail} |")

    return "\n".join(lines)


def write_report(
    result: ComparisonResult,
    output_path: Path,
    *,
    include_identical: bool = False,
    hash_files: bool = True
) -> None:
    """
    Write JSON report to file.

    Args:
        result: ComparisonResult to write.
        output_path: Path to output JSON file.
        include_identical: Whether to include identical files in details.
        hash_files: Whether SHA-256 hashing was enabled.
    """
    report = generate_report(
        result,
        include_identical=include_identical,
        hash_files=hash_files
    )
    output_path.write_text(json.dumps(report, indent=2, sort_keys=True))