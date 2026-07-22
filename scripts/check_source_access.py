#!/usr/bin/env python3
"""Validate that the publication token can read configured source repositories."""

from __future__ import annotations

import argparse
import json
import os
import urllib.error
import urllib.request
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


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", type=Path, default=Path("config/repositories.json"))
    parser.add_argument("--repository", default=os.environ.get("PUBLISH_REPOSITORY") or None)
    parser.add_argument("--secrets-file", type=Path)
    args = parser.parse_args()

    config = load_config(args.config)
    repositories = [repo for repo in config["repositories"] if matches(repo, args.repository)]
    if args.repository and not repositories:
        raise SystemExit(f"Repository is not configured: {args.repository}")

    local_secrets = load_secrets(args.secrets_file)
    token = (os.environ.get("PUBLISH_TOKEN") or local_secrets.get("PUBLISH_TOKEN", "")).strip()
    if not token and any(repo.get("private", True) for repo in repositories):
        raise SystemExit("PUBLISH_TOKEN is required to validate private source repositories")

    for repository in repositories:
        if not repository.get("private", True):
            continue
        full_name = f"{repository['owner']}/{repository['repo']}"
        request = urllib.request.Request(
            f"https://api.github.com/repos/{full_name}",
            headers={
                "Accept": "application/vnd.github+json",
                "Authorization": f"Bearer {token}",
                "X-GitHub-Api-Version": "2022-11-28",
            },
        )
        try:
            with urllib.request.urlopen(request, timeout=30) as response:
                if response.status != 200:
                    raise SystemExit(f"Unexpected GitHub API status for {full_name}: {response.status}")
        except urllib.error.HTTPError as error:
            if error.code == 401:
                reason = "invalid or expired"
            elif error.code == 403:
                reason = "blocked by organization policy or lacking permission"
            elif error.code == 404:
                reason = "not authorized for this repository, or repository not found"
            else:
                reason = f"HTTP {error.code}"
            raise SystemExit(f"PUBLISH_TOKEN cannot read {full_name}: {reason}") from error
        except urllib.error.URLError as error:
            raise SystemExit(f"Could not contact GitHub API for {full_name}: {error.reason}") from error
        print(f"PUBLISH_TOKEN can read {full_name}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
