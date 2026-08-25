#!/usr/bin/env python3
"""Comprueba que los activos públicos del libro no incluyan datos restringidos."""

from __future__ import annotations

import argparse
import csv
import json
import re
import sys
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
CONFIG_PATH = REPO_ROOT / "config" / "publication_assets.json"
PUBLIC_ASSET_DIRS = ("figures", "tables", "multiqc")
PATH_PATTERN = re.compile(r"(?:^|[\\\"'>( ])/(?:mnt|home|tmp|var/tmp|Users|private)(?:/|$)")


def load_config() -> dict:
    with CONFIG_PATH.open(encoding="utf-8") as handle:
        return json.load(handle)


def contains_blocked_extension(path: Path, extensions: list[str]) -> bool:
    name = path.name.lower()
    return any(name.endswith(extension) for extension in extensions)


def check_table_header(path: Path, restricted: set[str]) -> list[str]:
    if path.suffix.lower() not in {".tsv", ".csv"}:
        return []
    delimiter = "\t" if path.suffix.lower() == ".tsv" else ","
    with path.open(encoding="utf-8", newline="") as handle:
        header = next(csv.reader(handle, delimiter=delimiter), [])
    found = restricted.intersection(item.strip().lower() for item in header)
    return [f"{path.relative_to(REPO_ROOT)}: cabecera restringida {item}" for item in sorted(found)]


def check_text(path: Path) -> list[str]:
    if path.suffix.lower() not in {".tsv", ".csv", ".txt", ".html", ".json"}:
        return []
    content = path.read_text(encoding="utf-8", errors="replace")
    if PATH_PATTERN.search(content):
        return [f"{path.relative_to(REPO_ROOT)}: contiene una ruta absoluta restringida"]
    return []


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--include-docs",
        action="store_true",
        help="Incluye HTML generado en docs/ en la comprobación de rutas.",
    )
    args = parser.parse_args()
    config = load_config()
    restricted_headers = {item.lower() for item in config["restricted_table_headers"]}
    errors: list[str] = []

    roots = [REPO_ROOT / name for name in PUBLIC_ASSET_DIRS]
    if args.include_docs:
        roots.append(REPO_ROOT / "docs")
    for root in roots:
        if not root.exists():
            continue
        for path in root.rglob("*"):
            if not path.is_file():
                continue
            if contains_blocked_extension(path, config["blocked_extensions"]):
                errors.append(f"{path.relative_to(REPO_ROOT)}: extensión no publicable")
            errors.extend(check_table_header(path, restricted_headers))
            errors.extend(check_text(path))

    if errors:
        print("[validate] Se han detectado activos no publicables:", file=sys.stderr)
        print("\n".join(f"- {item}" for item in errors), file=sys.stderr)
        return 1
    print("[validate] activos públicos validados")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
