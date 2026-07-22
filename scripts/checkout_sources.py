#!/usr/bin/env python3
"""Checkout only the configured source repositories for a publication run."""

from __future__ import annotations

import argparse
import json
import os
import shutil
import subprocess
from pathlib import Path

from publish_secrets import load_secrets


def load_config(path: Path) -> dict:
    with path.open(encoding="utf-8") as handle:
        config = json.load(handle)
    repositories = config.get("repositories")
    if not isinstance(repositories, list) or not repositories:
        raise SystemExit("Configuration must contain a non-empty repositories list")
    return config


def matches(repository: dict, selector: str | None) -> bool:
    if not selector:
        return True
    full_name = f"{repository['owner']}/{repository['repo']}"
    return selector in {repository["id"], repository["repo"], full_name}


def selected_repositories(config: dict, selector: str | None) -> list[dict]:
    selected = [repo for repo in config["repositories"] if matches(repo, selector)]
    if selector and not selected:
        raise SystemExit(f"Repository is not configured: {selector}")
    return selected


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", type=Path, default=Path("config/repositories.json"))
    parser.add_argument("--output", type=Path, default=Path(".sources"))
    parser.add_argument("--repository", default=os.environ.get("PUBLISH_REPOSITORY") or None, help="Configured id, owner/repo, or repository name")
    parser.add_argument("--ref", default=os.environ.get("PUBLISH_REF") or None, help="Override the configured branch, tag, or commit")
    parser.add_argument("--secrets-file", type=Path, help="Optional ignored JSON file with local secrets")
    args = parser.parse_args()

    config = load_config(args.config)
    repositories = selected_repositories(config, args.repository)
    args.output.mkdir(parents=True, exist_ok=True)

    local_secrets = load_secrets(args.secrets_file)
    token = os.environ.get("PUBLISH_TOKEN") or local_secrets.get("PUBLISH_TOKEN", "")
    if any(repository.get("private", True) for repository in repositories) and not token:
        raise SystemExit(
            "PUBLISH_TOKEN no está disponible. Créalo como Repository secret en "
            "dodero/dodero.github.io, con el nombre exacto PUBLISH_TOKEN."
        )
    git_env = os.environ.copy()
    if token:
        # Keep the credential out of the clone command line and logs.
        git_env["GIT_CONFIG_COUNT"] = "1"
        git_env["GIT_CONFIG_KEY_0"] = "http.https://github.com/.extraheader"
        git_env["GIT_CONFIG_VALUE_0"] = f"AUTHORIZATION: bearer {token}"

    for repository in repositories:
        ref = args.ref if args.ref and (args.repository or len(repositories) == 1) else repository.get("ref")
        if not ref:
            raise SystemExit(f"No ref configured for {repository['owner']}/{repository['repo']}")

        destination = (args.output / repository["id"]).resolve()
        output_root = args.output.resolve()
        if output_root not in destination.parents:
            raise SystemExit("Invalid checkout destination")
        if destination.exists():
            shutil.rmtree(destination)

        url = f"https://github.com/{repository['owner']}/{repository['repo']}.git"
        print(f"Checking out {repository['owner']}/{repository['repo']}@{ref}")
        subprocess.run(
            ["git", "clone", "--depth", "1", "--branch", ref, url, str(destination)],
            check=True,
            env=git_env,
        )

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
