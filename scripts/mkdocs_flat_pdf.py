#!/usr/bin/env python3
"""Print every MkDocs content page and merge it into one flat PDF."""

from __future__ import annotations

import argparse
import re
import subprocess
import tempfile
from pathlib import Path

from pypdf import PdfWriter


def page_title(path: Path) -> str:
    content = path.read_text(encoding="utf-8", errors="replace")
    match = re.search(r"<title>(.*?)</title>", content, flags=re.IGNORECASE | re.DOTALL)
    if match:
        return re.sub(r"\s+", " ", match.group(1)).strip()
    return path.parent.name.replace("-", " ").title() or "Inicio"


def content_pages(site_dir: Path) -> list[Path]:
    pages = [
        path
        for path in site_dir.rglob("*.html")
        if path.name != "404.html" and "assets" not in path.relative_to(site_dir).parts
    ]
    return sorted(pages, key=lambda path: (path != site_dir / "index.html", path.relative_to(site_dir).as_posix()))


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--site-dir", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--browser-path", required=True)
    args = parser.parse_args()

    site_dir = args.site_dir.resolve()
    pages = content_pages(site_dir)
    if not pages:
        raise SystemExit(f"No MKDocs HTML pages found in {site_dir}")

    writer = PdfWriter()
    with tempfile.TemporaryDirectory(prefix="mkdocs-pdf-") as temp_name:
        temp_dir = Path(temp_name)
        for position, page in enumerate(pages):
            part = temp_dir / f"{position:04d}.pdf"
            subprocess.run(
                [
                    args.browser_path,
                    "--headless=new",
                    "--disable-gpu",
                    "--no-sandbox",
                    "--no-pdf-header-footer",
                    f"--print-to-pdf={part}",
                    page.as_uri(),
                ],
                check=True,
            )
            if not part.is_file():
                raise SystemExit(f"Chrome did not produce {part}")
            writer.append(str(part), outline_item=page_title(page))

    args.output.parent.mkdir(parents=True, exist_ok=True)
    with args.output.open("wb") as output:
        writer.write(output)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
