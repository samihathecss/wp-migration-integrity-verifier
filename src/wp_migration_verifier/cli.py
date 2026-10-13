"""
Command-line interface for WP Migration Integrity Verifier.
"""

import sys
from pathlib import Path

import click

from .compare import compare_inventories
from .report import generate_markdown, write_report


@click.command()
@click.argument("source", type=click.Path(exists=True, file_okay=False, dir_okay=True, path_type=Path))
@click.argument("destination", type=click.Path(exists=True, file_okay=False, dir_okay=True, path_type=Path))
@click.option(
    "-o", "--output",
    type=click.Path(file_okay=True, dir_okay=False, path_type=Path),
    default="migration-report.json",
    help="Output JSON report file."
)
@click.option(
    "--no-hash",
    is_flag=True,
    help="Skip SHA-256 hashing (compare by size only)."
)
@click.option(
    "--include-identical",
    is_flag=True,
    help="Include identical files in report details."
)
@click.option(
    "--chunk-size",
    type=int,
    default=1024 * 1024,
    help="Chunk size for streaming hash (bytes)."
)
@click.option(
    "-q", "--quiet",
    is_flag=True,
    help="Suppress progress output."
)
@click.option(
    "--markdown",
    is_flag=True,
    help="Also write a Markdown report alongside JSON."
)
@click.pass_context
def main(
    ctx: click.Context,
    source: Path,
    destination: Path,
    output: Path,
    no_hash: bool,
    include_identical: bool,
    chunk_size: int,
    quiet: bool,
    markdown: bool
) -> None:
    """
    Verify WordPress migration by comparing source and destination directories.

    Compares file inventories, sizes, and SHA-256 hashes to identify missing,
    added, or changed files. Generates a JSON report.

    Example:
        wp-migration-verify /path/to/source /path/to/dest -o report.json
    """
    if not quiet:
        click.echo(f"Scanning source: {source}")
        click.echo(f"Scanning destination: {destination}")

    try:
        result = compare_inventories(
            source_root=source,
            dest_root=destination,
            hash_files=not no_hash,
            chunk_size=chunk_size
        )
    except Exception as e:
        click.echo(f"Error during comparison: {e}", err=True)
        ctx.exit(1)

    write_report(result, output, include_identical=include_identical, hash_files=not no_hash)

    if markdown:
        md_path = output.with_suffix(".md")
        md_content = generate_markdown(
            result,
            include_identical=include_identical,
            hash_files=not no_hash
        )
        md_path.write_text(md_content, encoding="utf-8")
        if not quiet:
            click.echo(f"Markdown report written to: {md_path}")

    if not quiet:
        click.echo(f"\nReport written to: {output}")
        click.echo(f"Summary: {result.summary}")
        click.echo("\nNote: This tool only compares files. It does not verify")
        click.echo("database content, configuration correctness, or runtime behavior.")

    # Exit with non-zero if there are differences (missing, added, changed, errors)
    has_differences = any(
        result.summary.get(k, 0) > 0
        for k in ("missing", "added", "changed", "error")
    )
    ctx.exit(1 if has_differences else 0)


if __name__ == "__main__":
    main()