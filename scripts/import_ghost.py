#!/usr/bin/env python3
"""Import a Ghost JSON export into this Hugo site.

The source export is intentionally read from outside the repository. It may contain
user and site metadata that should not be committed.
"""

from __future__ import annotations

import argparse
import html
import json
import re
import sys
import urllib.error
import urllib.request
from collections import defaultdict
from pathlib import Path


IMAGE_RE = re.compile(
    r"(?:(?:https?:)?//blog\.badgerops\.net|__GHOST_URL__)?"
    r"/content/images/(?:size/w\d+/)?([^\"'\s>?]+)",
    re.IGNORECASE,
)
IMAGE_PREFIX_RE = re.compile(
    r"(?:(?:https?:)?//blog\.badgerops\.net|__GHOST_URL__)?"
    r"/content/images/(?:size/w\d+/)?",
    re.IGNORECASE,
)


def yaml_value(value: object) -> str:
    """JSON scalar/array syntax is valid YAML and avoids hand-rolled escaping."""
    return json.dumps(value, ensure_ascii=False)


def clean_excerpt(value: str | None, plaintext: str | None) -> str:
    source = value or plaintext or ""
    source = html.unescape(re.sub(r"\s+", " ", source)).strip()
    if len(source) <= 240:
        return source
    return source[:237].rsplit(" ", 1)[0] + "…"


def ghost_time(value: str | None) -> str | None:
    if not value:
        return None
    value = value.strip().replace(" ", "T")
    return value if value.endswith("Z") else value + "Z"


def normalize_body(body: str) -> str:
    # Ghost's responsive variants disappear with the Ghost image service. Point
    # every image at the original local copy and let the browser size it.
    body = re.sub(r"\s+srcset=(['\"]).*?\1", "", body, flags=re.DOTALL | re.IGNORECASE)
    body = re.sub(r"\s+sizes=(['\"]).*?\1", "", body, flags=re.DOTALL | re.IGNORECASE)
    body = IMAGE_PREFIX_RE.sub("/images/", body)
    body = body.replace("__GHOST_URL__", "https://blog.badgerops.net")
    # The site template owns the article title. A couple of Ghost posts also
    # embedded an H1 as their first card, which would otherwise render twice.
    body = re.sub(r"^\s*<h1\b[^>]*>.*?</h1>\s*", "", body, count=1, flags=re.DOTALL | re.IGNORECASE)
    return "\n".join(line.rstrip() for line in body.splitlines()).strip()


def image_paths(data: dict) -> set[str]:
    paths: set[str] = set()
    for post in data.get("posts", []):
        values = [post.get("html") or "", post.get("feature_image") or ""]
        for value in values:
            paths.update(match.group(1) for match in IMAGE_RE.finditer(value))
    for setting in data.get("settings", []):
        if setting.get("key") in {"cover_image", "icon", "logo"}:
            paths.update(match.group(1) for match in IMAGE_RE.finditer(setting.get("value") or ""))
    return {path.split("?", 1)[0] for path in paths}


def download_images(paths: set[str], destination: Path, base_url: str) -> None:
    failures: list[str] = []
    for index, relative in enumerate(sorted(paths), start=1):
        target = destination / relative
        if target.exists() and target.stat().st_size:
            print(f"[{index:02}/{len(paths):02}] keep {relative}")
            continue
        target.parent.mkdir(parents=True, exist_ok=True)
        url = f"{base_url.rstrip('/')}/content/images/{relative}"
        request = urllib.request.Request(url, headers={"User-Agent": "BadgerOps Ghost migration/1.0"})
        try:
            with urllib.request.urlopen(request, timeout=30) as response:
                target.write_bytes(response.read())
            print(f"[{index:02}/{len(paths):02}] fetch {relative}")
        except (urllib.error.URLError, TimeoutError) as error:
            failures.append(f"{url}: {error}")
            print(f"[{index:02}/{len(paths):02}] FAIL {relative}", file=sys.stderr)
    if failures:
        print("\nImage download failures:", file=sys.stderr)
        print("\n".join(f"  - {failure}" for failure in failures), file=sys.stderr)
        raise SystemExit(1)


def render_front_matter(post: dict, topics: list[str], *, aliases: list[str] | None = None) -> str:
    published = ghost_time(post.get("published_at"))
    created = ghost_time(post.get("created_at"))
    updated = ghost_time(post.get("updated_at"))
    is_draft = post.get("status") != "published"
    date = published or created or updated
    description = clean_excerpt(post.get("custom_excerpt"), post.get("plaintext"))
    lines = [
        "---",
        f"title: {yaml_value(post.get('title') or 'Untitled')}",
        f"slug: {yaml_value(post.get('slug') or post.get('id'))}",
    ]
    if date:
        lines.append(f"date: {date}")
    if updated:
        lines.append(f"lastmod: {updated}")
    lines.extend(
        [
            f"draft: {'true' if is_draft else 'false'}",
            f"description: {yaml_value(description)}",
            f"topics: {yaml_value(topics)}",
        ]
    )
    if post.get("featured"):
        lines.append("featured: true")
    if aliases:
        lines.append(f"aliases: {yaml_value(aliases)}")
    feature_image = post.get("feature_image")
    if feature_image:
        lines.append(f"image: {yaml_value(normalize_body(feature_image))}")
    lines.extend(["migration_source: ghost", "---", ""])
    return "\n".join(lines)


def import_content(data: dict, content_root: Path, *, include_drafts: bool = False) -> tuple[int, int, int]:
    tag_names = {
        tag["id"]: tag.get("name") or tag.get("slug")
        for tag in data.get("tags", [])
        if tag.get("id") and not (tag.get("slug") or "").startswith("hash-")
    }
    tags_by_post: dict[str, list[str]] = defaultdict(list)
    for relation in data.get("posts_tags", []):
        name = tag_names.get(relation.get("tag_id"))
        if name:
            tags_by_post[relation["post_id"]].append(name)

    posts_dir = content_root / "posts"
    posts_dir.mkdir(parents=True, exist_ok=True)
    pages = [post for post in data.get("posts", []) if post.get("type") == "page"]
    posts = [
        post
        for post in data.get("posts", [])
        if post.get("type") == "post" and (include_drafts or post.get("status") == "published")
    ]

    published_count = 0
    draft_count = 0
    for post in posts:
        slug = post.get("slug") or post["id"]
        topics = sorted(set(tags_by_post.get(post["id"], [])), key=str.casefold)
        published = post.get("status") == "published"
        aliases: list[str] = []
        if post.get("published_at"):
            year, month, day = post["published_at"][:10].split("-")
            aliases.append(f"/{year}/{month}/{day}/{slug}/")
        front_matter = render_front_matter(post, topics, aliases=aliases)
        body = normalize_body(post.get("html") or "")
        (posts_dir / f"{slug}.md").write_text(front_matter + body + "\n", encoding="utf-8")
        if published:
            published_count += 1
        else:
            draft_count += 1

    published_pages = [page for page in pages if page.get("status") == "published"]
    about_candidates = [page for page in published_pages if page.get("slug", "").startswith("about")]
    page_count = 0
    about_path = content_root / "about.md"
    if about_candidates and not about_path.exists():
        about = max(about_candidates, key=lambda page: page.get("published_at") or "")
        older_aliases = [f"/{page['slug']}/" for page in about_candidates if page["id"] != about["id"]]
        front_matter = render_front_matter(about, [], aliases=older_aliases)
        about_path.write_text(front_matter + normalize_body(about.get("html") or "") + "\n", encoding="utf-8")
        page_count += 1

    return published_count, draft_count, page_count


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("export", type=Path, help="Ghost JSON export")
    parser.add_argument("--content-root", type=Path, default=Path("content"))
    parser.add_argument("--assets-root", type=Path, default=Path("static/images"))
    parser.add_argument("--base-url", default="https://blog.badgerops.net")
    parser.add_argument("--download-assets", action="store_true")
    parser.add_argument(
        "--include-drafts",
        action="store_true",
        help="Import unpublished posts too (their source will be visible in a public repository)",
    )
    args = parser.parse_args()

    payload = json.loads(args.export.read_text(encoding="utf-8"))
    databases = payload.get("db") or []
    if not databases or not isinstance(databases[0].get("data"), dict):
        raise SystemExit("This does not look like a supported Ghost export")
    data = databases[0]["data"]

    published, drafts, pages = import_content(data, args.content_root, include_drafts=args.include_drafts)
    paths = image_paths(data)
    print(f"Imported {published} published posts, {drafts} drafts, and {pages} page.")
    print(f"Found {len(paths)} original Ghost image assets.")
    if args.download_assets:
        download_images(paths, args.assets_root, args.base_url)


if __name__ == "__main__":
    main()
