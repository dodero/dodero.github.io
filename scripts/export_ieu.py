#!/usr/bin/env python3
"""Export one IEU document and its local resources into a catalog entry."""

from __future__ import annotations

import argparse
import shutil
from pathlib import Path


MATERIALS = (
    "apuntes",
    "clase",
)


def export_html(source: Path, material: str, target: Path) -> None:
    target.parent.mkdir(parents=True, exist_ok=True)
    shutil.copyfile(source / f"{material}.html", target)
    shutil.copytree(source / "images", target.parent / "images", dirs_exist_ok=True)
    readings = source.parent / "lecturas"
    for reading in readings.glob("*.pdf"):
        destination = target.parent / "lecturas" / reading.name
        destination.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(reading, destination)
    if material != "apuntes":
        # Slides link to this local copy, preserving anchors and offline packages.
        shutil.copyfile(source / "apuntes.html", target.parent / "apuntes.html")
    else:
        # Retain the HTML/PDF URLs shared before the catalog was split into entries.
        for name in MATERIALS:
            for suffix in ("html", "pdf"):
                shutil.copyfile(source / f"{name}.{suffix}", target.parent / f"{name}.{suffix}")
    shutil.copyfile(source / "slides.css", target.parent / "slides.css")
    shutil.copytree(source / "reveal.js", target.parent / "reveal.js", dirs_exist_ok=True)
    # Asciidoctor's highlighter still references the pre-v6 CSS location.
    shutil.copytree(
        source / "reveal.js/dist/plugin/highlight",
        target.parent / "reveal.js/plugin/highlight",
        dirs_exist_ok=True,
    )


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", type=Path, required=True)
    parser.add_argument("--material", choices=MATERIALS, required=True)
    output = parser.add_mutually_exclusive_group(required=True)
    output.add_argument("--html", type=Path)
    output.add_argument("--pdf", type=Path)
    args = parser.parse_args()
    if args.html:
        export_html(args.input, args.material, args.html)
    else:
        args.pdf.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(args.input / f"{args.material}.pdf", args.pdf)


if __name__ == "__main__":
    main()
