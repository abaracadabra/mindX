# SPDX-License-Identifier: Apache-2.0
# (c) 2026 BANKON — all rights reserved.
"""Command-line interface for WordPress.agent.

Usage examples:
    wordpress-agent health
    wordpress-agent publish --title "Hello" --content-file post.html
    wordpress-agent publish --title "Scheduled" --content-file post.html \\
        --status future --date 2026-06-01T09:00:00+00:00
    wordpress-agent media upload --file image.png --alt "Featured image"
"""
from __future__ import annotations

import asyncio
import json
import sys
from datetime import datetime
from pathlib import Path

import click

from . import __version__
from .agent import WordpressAgent
from .config import Settings


def _settings() -> Settings:
    try:
        return Settings()  # type: ignore[call-arg]
    except Exception as exc:  # pragma: no cover
        click.echo(f"Configuration error: {exc}", err=True)
        sys.exit(2)


def _emit(data: dict) -> None:
    click.echo(json.dumps(data, indent=2, default=str))


@click.group()
@click.version_option(version=__version__, prog_name="wordpress-agent")
def main() -> None:
    """WordPress.agent — agnostic publishing tool."""


@main.command()
def health() -> None:
    """Verify connectivity and authentication."""

    async def _run() -> None:
        async with WordpressAgent(_settings()) as agent:
            result = await agent.health_check()
            _emit(result)
            if not result["ok"]:
                sys.exit(1)

    asyncio.run(_run())


@main.command()
@click.option("--title", required=True, help="Post title.")
@click.option(
    "--content-file",
    type=click.Path(exists=True, dir_okay=False, path_type=Path),
    help="Path to a file containing the post content (HTML or block markup).",
)
@click.option(
    "--content",
    help="Inline content. Mutually exclusive with --content-file.",
)
@click.option(
    "--status",
    type=click.Choice(["publish", "future", "draft", "pending", "private"]),
    default="publish",
    show_default=True,
)
@click.option(
    "--date",
    type=click.DateTime(formats=["%Y-%m-%dT%H:%M:%S%z", "%Y-%m-%dT%H:%M:%S"]),
    help="Scheduled publish datetime (ISO 8601). Required when status=future.",
)
@click.option("--category", "categories", type=int, multiple=True, help="Category ID (repeatable).")
@click.option("--tag", "tags", type=int, multiple=True, help="Tag ID (repeatable).")
@click.option("--featured-media", type=int, help="Featured media ID.")
@click.option("--excerpt", help="Optional excerpt text.")
@click.option("--slug", help="Optional URL slug.")
def publish(
    title: str,
    content_file: Path | None,
    content: str | None,
    status: str,
    date: datetime | None,
    categories: tuple[int, ...],
    tags: tuple[int, ...],
    featured_media: int | None,
    excerpt: str | None,
    slug: str | None,
) -> None:
    """Publish a finished article to WordPress."""
    if content_file is None and content is None:
        raise click.UsageError("Provide either --content or --content-file")
    if content_file is not None and content is not None:
        raise click.UsageError("--content and --content-file are mutually exclusive")
    if status == "future" and date is None:
        raise click.UsageError("--date is required when --status=future")

    body = content if content is not None else content_file.read_text(encoding="utf-8")  # type: ignore[union-attr]

    async def _run() -> None:
        async with WordpressAgent(_settings()) as agent:
            result = await agent.publish(
                title=title,
                content=body,
                status=status,  # type: ignore[arg-type]
                date=date,
                categories=list(categories) if categories else None,
                tags=list(tags) if tags else None,
                featured_media=featured_media,
                excerpt=excerpt,
                slug=slug,
            )
            _emit(
                {
                    "post_id": result.post_id,
                    "url": result.url,
                    "status": result.status,
                    "slug": result.slug,
                    "date_gmt": result.date_gmt,
                }
            )

    asyncio.run(_run())


@main.group()
def media() -> None:
    """Media operations."""


@media.command("upload")
@click.option(
    "--file",
    "file_path",
    type=click.Path(exists=True, dir_okay=False, path_type=Path),
    required=True,
    help="Local path to the file to upload.",
)
@click.option("--alt", "alt_text", default="", help="Alt text for accessibility and SEO.")
@click.option("--caption", default="", help="Caption text.")
@click.option("--title", "media_title", help="Optional media title override.")
def media_upload(
    file_path: Path,
    alt_text: str,
    caption: str,
    media_title: str | None,
) -> None:
    """Upload a media file (typically a featured image)."""

    async def _run() -> None:
        async with WordpressAgent(_settings()) as agent:
            result = await agent.upload_media(
                file_path,
                alt_text=alt_text,
                caption=caption,
                title=media_title,
            )
            _emit(
                {
                    "media_id": result.media_id,
                    "url": result.url,
                    "mime_type": result.mime_type,
                }
            )

    asyncio.run(_run())


if __name__ == "__main__":
    main()
