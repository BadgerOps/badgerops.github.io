#!/usr/bin/env python3
"""Small dependency-free smoke test for the generated Hugo site."""

from __future__ import annotations

import json
import sys
from html.parser import HTMLParser
from pathlib import Path, PurePosixPath
from urllib.parse import unquote, urlsplit


class AssetParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self.assets: list[str] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        values = dict(attrs)
        if tag in {"img", "script", "source", "video"} and values.get("src"):
            self.assets.append(values["src"] or "")
        if tag == "link" and values.get("href") and values.get("rel") in {"stylesheet", "icon"}:
            self.assets.append(values["href"] or "")


def local_asset(root: Path, document: Path, url: str) -> Path | None:
    split = urlsplit(url)
    if split.scheme or split.netloc or url.startswith(("data:", "#")):
        return None
    path = unquote(split.path)
    if not path:
        return None
    if path.startswith("/"):
        return root / path.lstrip("/")
    return document.parent / PurePosixPath(path)


def main() -> None:
    root = Path(sys.argv[1] if len(sys.argv) > 1 else "public").resolve()
    required = ["index.html", "posts/index.html", "topics/index.html", "about/index.html", "404.html", "index.json", "index.xml"]
    errors = [f"missing required output: {path}" for path in required if not (root / path).exists()]

    index_path = root / "index.json"
    if index_path.exists():
        try:
            search = json.loads(index_path.read_text(encoding="utf-8"))
            if len(search) < 20:
                errors.append(f"search index has only {len(search)} entries")
        except json.JSONDecodeError as error:
            errors.append(f"invalid search index JSON: {error}")

    for document in root.rglob("*.html"):
        source = document.read_text(encoding="utf-8")
        for marker in ("__GHOST_URL__", "/content/images/"):
            if marker in source:
                errors.append(f"unresolved Ghost marker {marker!r} in {document.relative_to(root)}")
        parser = AssetParser()
        parser.feed(source)
        for url in parser.assets:
            asset = local_asset(root, document, url)
            if asset is not None and not asset.exists():
                errors.append(f"missing asset {url!r} referenced by {document.relative_to(root)}")

    if errors:
        print("Generated-site checks failed:", file=sys.stderr)
        for error in errors[:50]:
            print(f"  - {error}", file=sys.stderr)
        if len(errors) > 50:
            print(f"  ...and {len(errors) - 50} more", file=sys.stderr)
        raise SystemExit(1)
    print("Generated-site checks passed.")


if __name__ == "__main__":
    main()
