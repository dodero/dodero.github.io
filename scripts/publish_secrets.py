#!/usr/bin/env python3
"""Load optional local-only secrets without ever writing them to the site."""

from __future__ import annotations

import json
from pathlib import Path


def load_secrets(explicit_path: Path | None = None) -> dict[str, str]:
    candidates = [
        explicit_path,
        Path("config/local-secrets.json"),
        Path(".secrets/publish.json"),
    ]
    for candidate in candidates:
        if candidate is None or not candidate.is_file():
            continue
        try:
            values = json.loads(candidate.read_text(encoding="utf-8"))
        except json.JSONDecodeError as error:
            raise SystemExit(f"Invalid local secrets file: {candidate}: {error}") from error
        if not isinstance(values, dict):
            raise SystemExit(f"Local secrets file must contain a JSON object: {candidate}")
        return {str(key): str(value) for key, value in values.items() if value is not None}
    return {}
