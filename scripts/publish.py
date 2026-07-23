#!/usr/bin/env python3
"""Build configured source repositories into a static GitHub Pages tree."""

from __future__ import annotations

import argparse
import html as html_lib
import json
import os
import re
import shlex
import shutil
import subprocess
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import unquote, urlsplit

from publish_secrets import load_secrets


FORMATS = {"html", "pdf"}
BUILDERS = {"marp", "mkdocs", "asciidoctor", "github-markdown", "custom"}
SKIP_SITE_ENTRIES = {".git", ".github", ".secrets", ".sources", "config", "scripts", "dist", "node_modules"}
PRIVATE_SOURCE_SUFFIXES = {".md", ".markdown", ".mdown", ".mkd", ".adoc", ".ad", ".yml", ".yaml"}


def load_config(path: Path) -> dict:
    with path.open(encoding="utf-8") as handle:
        config = json.load(handle)
    repositories = config.get("repositories")
    if not isinstance(repositories, list) or not repositories:
        raise SystemExit("Configuration must contain a non-empty repositories list")
    seen: set[str] = set()
    for repository in repositories:
        repo_id = repository.get("id")
        if not repo_id or repo_id in seen:
            raise SystemExit(f"Invalid or duplicated repository id: {repo_id}")
        seen.add(repo_id)
        builder = repository.get("builder")
        if builder not in BUILDERS:
            raise SystemExit(f"Unsupported builder for {repo_id}: {builder}")
        formats = set(repository.get("formats", []))
        if not formats or not formats <= FORMATS:
            raise SystemExit(f"Invalid formats for {repo_id}: {sorted(formats)}")
        if not repository.get("sources"):
            raise SystemExit(f"No sources configured for {repo_id}")
    return config


def select_repositories(config: dict, selector: str | None) -> list[dict]:
    if not selector:
        return list(config["repositories"])
    selected = []
    for repository in config["repositories"]:
        full_name = f"{repository['owner']}/{repository['repo']}"
        if selector in {repository["id"], repository["repo"], full_name}:
            selected.append(repository)
    if not selected:
        raise SystemExit(f"Repository is not configured: {selector}")
    return selected


def slugify(value: str) -> str:
    value = value.strip().lower()
    value = re.sub(r"[^\w\s-]", "", value, flags=re.UNICODE)
    value = re.sub(r"[\s_-]+", "-", value)
    return value.strip("-") or "material"


def normalize_tags(values: list[str] | None) -> list[str]:
    tags = []
    for value in values or []:
        tag = str(value).strip().lstrip("#")
        if tag and tag not in tags:
            tags.append(tag)
    return tags


def run(command: list[str] | str, cwd: Path, *, shell: bool = False) -> None:
    shown = command if isinstance(command, str) else " ".join(shlex.quote(item) for item in command)
    print(f"$ {shown}")
    subprocess.run(command, cwd=cwd, check=True, shell=shell)


def install_pnpm_dependencies(repo_dir: Path, dependencies: list[str]) -> None:
    dependencies = list(dict.fromkeys(dependencies))
    if not dependencies:
        return
    run(
        ["pnpm", "add", "--save-dev", *dependencies],
        repo_dir,
    )


def sanitize_html(path: Path) -> None:
    content = path.read_text(encoding="utf-8", errors="replace")
    sanitized = re.sub(r"<!--[\s\S]*?-->", "", content)
    path.write_text(sanitized, encoding="utf-8")
    if "<!--" in sanitized:
        raise SystemExit(f"HTML comment remains after sanitization: {path}")


def copy_local_assets(html_path: Path, source_file: Path, repo_dir: Path) -> None:
    """Copy local files under a material-local assets directory and rewrite URLs."""
    content = html_path.read_text(encoding="utf-8", errors="replace")
    raw_content = content
    content = html_lib.unescape(content)
    references = re.findall(r"(?:src|href)=[\"']([^\"']+)[\"']|url\(\s*[\"']?([^)'\"]+)", content)
    source_dir = source_file.parent
    repo_root = repo_dir.resolve()
    replacements: dict[str, str] = {}
    for first, second in references:
        reference = (first or second).strip()
        parsed = urlsplit(reference)
        if parsed.scheme in {"http", "https", "data", "javascript", "mailto"} or reference.startswith(("#", "/")):
            continue
        if parsed.scheme == "file":
            candidate = Path(unquote(parsed.path)).resolve()
        else:
            relative = Path(unquote(parsed.path))
            candidate = (source_dir / relative).resolve()
        if not candidate.is_file() or repo_root not in candidate.parents:
            continue
        if candidate.suffix.lower() in PRIVATE_SOURCE_SUFFIXES:
            continue
        repository_relative = candidate.relative_to(repo_root)
        target = html_path.parent / "assets" / repository_relative
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(candidate, target)
        replacement = f"assets/{repository_relative.as_posix()}"
        if parsed.query:
            replacement += f"?{parsed.query}"
        if parsed.fragment:
            replacement += f"#{parsed.fragment}"
        replacements[reference] = replacement

    content = raw_content
    for original, replacement in replacements.items():
        content = content.replace(original, replacement)
        for quote in ("&quot;", "&#34;", "&apos;", "&#39;"):
            content = content.replace(f"{quote}{original}{quote}", f'"{replacement}"')
    html_path.write_text(content, encoding="utf-8")


def source_specs(repository: dict) -> list[dict]:
    specs = []
    for source in repository["sources"]:
        if isinstance(source, str):
            source = {"path": source}
        if not source.get("path"):
            raise SystemExit(f"Source without path in {repository['id']}")
        source = dict(source)
        source.setdefault("name", Path(source["path"]).stem)
        source["slug"] = slugify(source["name"])
        specs.append(source)
    return specs


def material_output(dist: Path, repository: dict, source: dict) -> tuple[Path, Path, str]:
    output_dir = dist / "materials" / repository["id"] / source["slug"]
    output_dir.mkdir(parents=True, exist_ok=True)
    html_path = output_dir / "index.html"
    pdf_path = output_dir / f"{source['slug']}.pdf"
    url_base = f"materials/{repository['id']}/{source['slug']}"
    return html_path, pdf_path, url_base


def run_marp(repository: dict, source_file: Path, html_path: Path, pdf_path: Path, repo_dir: Path, formats: set[str], browser_path: str | None) -> None:
    install_pnpm_dependencies(repo_dir, ["@marp-team/marp-cli", *repository.get("dependencies", [])])
    command_base = ["pnpm", "exec", "marp", "--allow-local-files"]
    engine = repository.get("engine")
    if engine:
        engine_path = (repo_dir / engine).resolve()
        if repo_dir.resolve() not in engine_path.parents or not engine_path.is_file():
            raise SystemExit(f"Marp engine not found inside source repository: {engine}")
        command_base += ["--config-file", str(engine_path)]
    if "html" in formats:
        run([*command_base, "--html", str(source_file), "-o", str(html_path)], repo_dir)
        sanitize_html(html_path)
        copy_local_assets(html_path, source_file, repo_dir)
    if "pdf" in formats:
        command = [*command_base, "--pdf", "--html", str(source_file)]
        if browser_path:
            command += ["--browser", "chrome", "--browser-path", browser_path]
        command += ["-o", str(pdf_path), "--pdf-outlines", "--pdf-outlines.pages=false", "--pdf-outlines.headings=true"]
        run(command, repo_dir)


def run_github_markdown(
    repository: dict,
    source: dict,
    source_file: Path,
    html_path: Path,
    pdf_path: Path,
    repo_dir: Path,
    formats: set[str],
    browser_path: str | None,
) -> None:
    """Render GitHub-Flavored Markdown with marked and print it through Chrome."""
    dependencies = repository.get("dependencies", ["marked"])
    install_pnpm_dependencies(repo_dir, dependencies)
    body_path = html_path.with_name(".github-markdown-body.html")
    run(
        [
            "pnpm",
            "exec",
            "marked",
            "--gfm",
            "--input",
            str(source_file),
            "--output",
            str(body_path),
        ],
        repo_dir,
    )
    body = body_path.read_text(encoding="utf-8", errors="replace")
    body_path.unlink(missing_ok=True)
    title = html_lib.escape(source.get("title", repository.get("title", source_file.stem)))
    html_path.write_text(
        """<!doctype html>
<html lang="es">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>"""
        + title
        + """</title>
  <style>
    :root { color-scheme: light; font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif; }
    body { margin: 0; color: #24292f; background: #fff; }
    main { max-width: 960px; margin: 0 auto; padding: 3rem 4rem; line-height: 1.6; }
    h1, h2, h3, h4 { line-height: 1.25; margin-top: 1.5em; }
    h1 { border-bottom: 1px solid #d0d7de; padding-bottom: .3em; }
    h2 { border-bottom: 1px solid #d8dee4; padding-bottom: .25em; }
    a { color: #0969da; }
    code, pre { font-family: ui-monospace, SFMono-Regular, Menlo, Consolas, monospace; }
    code { padding: .15em .3em; background: #eff1f3; border-radius: 4px; }
    pre { overflow-x: auto; padding: 1rem; background: #f6f8fa; border-radius: 6px; }
    pre code { padding: 0; background: transparent; }
    blockquote { margin: 1rem 0; padding: 0 1rem; color: #57606a; border-left: .25rem solid #d0d7de; }
    table { border-collapse: collapse; width: 100%; }
    th, td { padding: .5rem .75rem; border: 1px solid #d0d7de; }
    th { background: #f6f8fa; }
    img { max-width: 100%; height: auto; }
    @media print {
      main { max-width: none; padding: 0; }
      pre, blockquote, table, img { break-inside: avoid; }
    }
  </style>
</head>
<body><main>"""
        + body
        + """</main></body>
</html>
""",
        encoding="utf-8",
    )
    sanitize_html(html_path)
    copy_local_assets(html_path, source_file, repo_dir)
    if "pdf" in formats:
        if not browser_path:
            raise SystemExit("GitHub Markdown PDF output needs --browser-path")
        run(
            [
                browser_path,
                "--headless=new",
                "--disable-gpu",
                "--no-sandbox",
                "--no-pdf-header-footer",
                f"--print-to-pdf={pdf_path}",
                html_path.resolve().as_uri(),
            ],
            repo_dir,
        )
        if not pdf_path.is_file():
            raise SystemExit(f"Chrome did not produce {pdf_path}")
    if "html" not in formats:
        html_path.unlink(missing_ok=True)


def run_template(command: str, values: dict[str, str], repo_dir: Path) -> None:
    if re.search(r"\bnpm\b", command):
        raise SystemExit("Builder commands must use pnpm instead of npm")
    rendered = command.format(**values)
    run(rendered, repo_dir, shell=True)


def run_mkdocs(repository: dict, repo_dir: Path, output_dir: Path, html_path: Path, pdf_path: Path, formats: set[str]) -> None:
    site_dir = output_dir / "_mkdocs-site"
    command = ["mkdocs", "build", "--clean", "--site-dir", str(site_dir)]
    if repository.get("config"):
        command += ["--config-file", str((repo_dir / repository["config"]).resolve())]
    run(command, repo_dir)
    if "html" in formats:
        for child in site_dir.iterdir():
            target = output_dir / child.name
            if child.is_dir():
                shutil.copytree(child, target, dirs_exist_ok=True)
            else:
                shutil.copy2(child, target)
        if not html_path.exists():
            raise SystemExit(f"MKDocs did not produce {html_path}")
        sanitize_html(html_path)
        shutil.rmtree(site_dir)
    if "pdf" in formats:
        pdf_command = repository.get("pdf_command")
        if not pdf_command:
            raise SystemExit(f"MKDocs repository {repository['id']} needs pdf_command for PDF output")
        run_template(pdf_command, {"repo": str(repo_dir), "out_dir": str(output_dir), "pdf": str(pdf_path)}, repo_dir)


def run_asciidoctor(repository: dict, source_file: Path, html_path: Path, pdf_path: Path, repo_dir: Path, formats: set[str]) -> None:
    if "html" in formats:
        run([repository.get("html_command", "asciidoctor"), "-o", str(html_path), str(source_file)], repo_dir)
        sanitize_html(html_path)
    if "pdf" in formats:
        run([repository.get("pdf_command", "asciidoctor-pdf"), "-o", str(pdf_path), str(source_file)], repo_dir)


def run_custom(repository: dict, source_file: Path, html_path: Path, pdf_path: Path, output_dir: Path, repo_dir: Path, formats: set[str]) -> None:
    values = {"source": str(source_file), "html": str(html_path), "pdf": str(pdf_path), "out_dir": str(output_dir), "repo": str(repo_dir)}
    commands = repository.get("commands", {})
    for output_format in formats:
        if output_format not in commands:
            raise SystemExit(f"Custom builder {repository['id']} has no command for {output_format}")
        run_template(commands[output_format], values, repo_dir)
        if output_format == "html":
            sanitize_html(html_path)


def prepare_dist(site_root: Path, dist: Path) -> None:
    if dist.exists():
        shutil.rmtree(dist)
    dist.mkdir(parents=True)
    for entry in site_root.iterdir():
        if entry.name in SKIP_SITE_ENTRIES:
            continue
        target = dist / entry.name
        if entry.is_dir():
            shutil.copytree(entry, target, dirs_exist_ok=True)
        else:
            shutil.copy2(entry, target)


def restore_previous_materials(dist: Path, previous_site: Path) -> bool:
    """Restore generated materials/catalog from the previous Pages artifact."""
    previous_site = previous_site.resolve()
    previous_materials = previous_site / "materials"
    if not previous_materials.is_dir():
        return False
    shutil.copytree(previous_materials, dist / "materials", dirs_exist_ok=True)
    previous_catalog = previous_site / "catalog.json"
    if previous_catalog.is_file():
        shutil.copy2(previous_catalog, dist / "catalog.json")
    return True


def read_existing_catalog(dist: Path) -> list[dict]:
    catalog = dist / "catalog.json"
    if not catalog.exists():
        return []
    try:
        return json.loads(catalog.read_text(encoding="utf-8")).get("materials", [])
    except (json.JSONDecodeError, AttributeError):
        return []


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", type=Path, default=Path("config/repositories.json"))
    parser.add_argument("--sources", type=Path, default=Path(".sources"))
    parser.add_argument("--site-root", type=Path, default=Path("."))
    parser.add_argument("--dist", type=Path, default=Path("dist"))
    parser.add_argument("--repository", default=None, help="Build only this configured repository")
    parser.add_argument("--ref", default=None, help="Override the selected repository ref")
    parser.add_argument("--browser-path")
    parser.add_argument("--previous-site", type=Path, help="Previous Pages site to preserve during a selective build")
    parser.add_argument("--secrets-file", type=Path, help="Optional ignored JSON file with local secrets")
    args = parser.parse_args()

    for key, value in load_secrets(args.secrets_file).items():
        os.environ.setdefault(key, value)

    config = load_config(args.config)
    repositories = select_repositories(config, args.repository)
    prepare_dist(args.site_root.resolve(), args.dist.resolve())
    if args.previous_site and not restore_previous_materials(args.dist.resolve(), args.previous_site):
        print(f"Previous Pages site has no materials directory: {args.previous_site}")
    existing = read_existing_catalog(args.dist.resolve())
    selected_ids = {repository["id"] for repository in repositories}
    if args.previous_site:
        for repository_id in selected_ids:
            shutil.rmtree(args.dist.resolve() / "materials" / repository_id, ignore_errors=True)
    selected_source_repositories = {(repository["owner"], repository["repo"]) for repository in repositories}
    selector_is_source_repository = bool(
        args.repository
        and any(
            args.repository in {repository["repo"], f"{repository['owner']}/{repository['repo']}"}
            for repository in config["repositories"]
        )
    )
    materials = [
        material
        for material in existing
        if material.get("repository_id") not in selected_ids
        and not (
            selector_is_source_repository
            and (material.get("owner"), material.get("repo")) in selected_source_repositories
        )
    ]

    for repository in repositories:
        repo_dir = (args.sources / repository["id"]).resolve()
        if not repo_dir.is_dir():
            raise SystemExit(f"Missing checkout for {repository['id']}: {repo_dir}")
        ref = args.ref if args.ref and (args.repository or len(repositories) == 1) else repository.get("ref", "")
        if not ref:
            raise SystemExit(f"No ref configured for {repository['id']}")
        formats = set(repository["formats"])
        for source in source_specs(repository):
            source_file = (repo_dir / source["path"]).resolve()
            if repo_dir.resolve() not in source_file.parents or not source_file.is_file():
                raise SystemExit(f"Source file not found inside {repository['id']}: {source['path']}")
            html_path, pdf_path, url_base = material_output(args.dist.resolve(), repository, source)
            builder = repository["builder"]
            if builder == "marp":
                run_marp(repository, source_file, html_path, pdf_path, repo_dir, formats, args.browser_path)
            elif builder == "github-markdown":
                run_github_markdown(repository, source, source_file, html_path, pdf_path, repo_dir, formats, args.browser_path)
            elif builder == "mkdocs":
                run_mkdocs(repository, repo_dir, html_path.parent, html_path, pdf_path, formats)
            elif builder == "asciidoctor":
                run_asciidoctor(repository, source_file, html_path, pdf_path, repo_dir, formats)
            else:
                run_custom(repository, source_file, html_path, pdf_path, html_path.parent, repo_dir, formats)

            material = {
                "repository_id": repository["id"],
                "owner": repository["owner"],
                "repo": repository["repo"],
                "ref": ref,
                "title": source.get("title", repository["title"]),
                "description": source.get("description", repository.get("description", "")),
                "icon": source.get("icon", repository.get("icon", "📄")),
                "subject": source.get("subject", repository.get("subject")),
                "degree": source.get("degree", repository.get("degree")),
                "event": source.get("event", repository.get("event")),
                "year": source.get("year", repository.get("year")),
                "tags": normalize_tags(source.get("tags", repository.get("tags", []))),
                "builder": builder,
                "formats": sorted(formats),
                "source_path": source["path"],
                "html": f"{url_base}/index.html" if "html" in formats else None,
                "pdf": f"{url_base}/{source['slug']}.pdf" if "pdf" in formats else None,
                "publish_source": bool(repository.get("publish_source", False)),
            }
            if material["publish_source"]:
                source_target = html_path.parent / source_file.name
                shutil.copy2(source_file, source_target)
                material["source"] = f"{url_base}/{source_file.name}"
            materials.append(material)

    catalog = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "materials": materials,
    }
    catalog_json = json.dumps(catalog, ensure_ascii=False, indent=2) + "\n"
    dist_root = args.dist.resolve()
    (dist_root / "catalog.json").write_text(catalog_json, encoding="utf-8")
    data_dir = dist_root / "_data"
    data_dir.mkdir(parents=True, exist_ok=True)
    (data_dir / "catalog.json").write_text(catalog_json, encoding="utf-8")
    print(f"Published {len(materials)} catalog entries")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
