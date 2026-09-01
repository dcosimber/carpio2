#!/usr/bin/env python3
"""Comprueba que los activos públicos del libro respeten la lista blanca de CARPIO."""

from __future__ import annotations

import argparse
import csv
import json
import re
import sys
import zipfile
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
CONFIG_PATH = REPO_ROOT / "config" / "publication_assets.json"
PUBLIC_ASSET_DIRS = ("data", "figures", "tables", "multiqc")
INCLUDE_ROOT = REPO_ROOT / "chapters" / "includes"
SOURCE_TEXT_DIRS = (REPO_ROOT / "chapters", REPO_ROOT / "appendices")
PATH_PATTERN = re.compile(r"/(?:mnt|home|tmp|var/tmp|Users|private)(?:/|\Z)")
HTML_ID_PATTERN = re.compile(r"^[a-z][a-z0-9-]*$")
CHAPTER_DIRECTORY_PATTERN = re.compile(
    r"^(?P<chapter>0?[1-9][0-9]?)_[a-z0-9]+(?:_[a-z0-9]+)*$"
)
TABLE_FILENAME_PATTERN = re.compile(
    r"^Table-(?P<chapter>[1-9][0-9]?)\.(?P<number>[1-9][0-9]*)-[a-z0-9]+(?:-[a-z0-9]+)*\.(?:tsv|csv)$"
)
FIGURE_FILENAME_PATTERN = re.compile(
    r"^Fig-(?P<chapter>[1-9][0-9]?)\.(?P<number>[1-9][0-9]*)-[a-z0-9]+(?:-[a-z0-9]+)*\.(?:png|pdf|svg|jpg|jpeg|webp)$"
)
MULTIQC_FILENAME_PATTERN = re.compile(
    r"^MultiQC-(?P<chapter>[1-9][0-9]?)\.(?P<number>[1-9][0-9]*)-[a-z0-9]+(?:-[a-z0-9]+)*\.html$"
)

# Es la misma excepción mínima que aplica el exportador. Un XLSX solo se acepta
# si está asociado a una de estas rutas completas, no por su extensión.
AUTHORIZED_METADATA_ASSETS = {
    "technical_metadata_tsv": {
        "source": "metadata/CARPIO_technical_metadata.tsv",
        "destination": "data/metadata/CARPIO_technical_metadata.tsv",
        "format": "tsv",
    },
    "technical_metadata_xlsx": {
        "source": "metadata/CARPIO_technical_metadata.xlsx",
        "destination": "data/metadata/CARPIO_technical_metadata.xlsx",
        "format": "xlsx",
    },
    "clinical_metadata_tsv": {
        "source": "metadata/CARPIO_clinical_metadata.tsv",
        "destination": "data/metadata/CARPIO_clinical_metadata.tsv",
        "format": "tsv",
    },
    "clinical_metadata_xlsx": {
        "source": "metadata/CARPIO_clinical_metadata.xlsx",
        "destination": "data/metadata/CARPIO_clinical_metadata.xlsx",
        "format": "xlsx",
    },
    "analysis_metadata_tsv": {
        "source": "metadata/CARPIO_analysis_metadata.tsv",
        "destination": "data/metadata/CARPIO_analysis_metadata.tsv",
        "format": "tsv",
    },
}


class ValidationError(RuntimeError):
    """Fallo controlado de la validación pública."""


def load_config() -> dict:
    with CONFIG_PATH.open(encoding="utf-8") as handle:
        return json.load(handle)


def repo_relative(path: Path) -> str:
    return path.relative_to(REPO_ROOT).as_posix()


def is_within(child: Path, parent: Path) -> bool:
    try:
        child.relative_to(parent)
    except ValueError:
        return False
    return True


def configured_metadata_assets(config: dict) -> dict[str, dict]:
    """Comprueba la lista blanca y devuelve los activos indexados por destino."""
    assets = config.get("authorized_metadata_assets")
    if not isinstance(assets, list):
        raise ValidationError("Falta la lista de activos de metadatos autorizados.")
    asset_ids = [asset.get("id") for asset in assets if isinstance(asset, dict)]
    if len(assets) != len(AUTHORIZED_METADATA_ASSETS) or set(asset_ids) != set(
        AUTHORIZED_METADATA_ASSETS
    ):
        raise ValidationError("La lista de metadatos no coincide con la lista blanca exacta.")

    by_destination: dict[str, dict] = {}
    table_ids: set[str] = set()
    includes: set[str] = set()
    for asset in assets:
        if not isinstance(asset, dict):
            raise ValidationError("Hay un activo de metadatos con formato inválido.")
        expected = AUTHORIZED_METADATA_ASSETS[asset["id"]]
        for key, expected_value in expected.items():
            if asset.get(key) != expected_value:
                raise ValidationError(
                    "La configuración de " + str(asset["id"]) + " no coincide con la lista blanca."
                )
        destination = str(asset["destination"])
        if destination in by_destination:
            raise ValidationError("Hay destinos de metadatos duplicados.")
        if not destination.startswith("data/metadata/"):
            raise ValidationError("Un metadato autorizado no se dirige a data/metadata/.")
        if not destination.lower().endswith("." + expected["format"]):
            raise ValidationError("La extensión de un metadato no coincide con su formato.")

        if expected["format"] == "xlsx":
            if "table" in asset or "expected_rows" in asset:
                raise ValidationError("Un XLSX autorizado no puede generar tabla paginada.")
        else:
            table = asset.get("table")
            if not isinstance(table, dict):
                raise ValidationError("Falta la configuración de una tabla paginada.")
            required = {
                "include_destination",
                "table_id",
                "table_label",
                "caption",
                "page_size",
            }
            if required.difference(table) or "expected_rows" not in asset:
                raise ValidationError("La configuración de tabla paginada está incompleta.")
            if int(asset["expected_rows"]) < 1 or int(table["page_size"]) < 1:
                raise ValidationError("El número de filas o el tamaño de página no es válido.")
            table_id = str(table["table_id"])
            include = str(table["include_destination"])
            if not HTML_ID_PATTERN.fullmatch(table_id):
                raise ValidationError("Un identificador HTML de tabla no es válido.")
            include_path = (REPO_ROOT / include).resolve()
            if not is_within(include_path, INCLUDE_ROOT):
                raise ValidationError("Un include de metadatos sale de chapters/includes/.")
            if table_id in table_ids or include in includes:
                raise ValidationError("Hay tablas paginadas de metadatos duplicadas.")
            table_ids.add(table_id)
            includes.add(include)

        by_destination[destination] = asset
    return by_destination


def contains_blocked_extension(path: Path, extensions: list[str]) -> bool:
    name = path.name.lower()
    return any(name.endswith(extension) for extension in extensions)


def check_report_asset_path(
    canonical_relative: str, metadata_asset: dict | None
) -> list[str]:
    """Exige rutas ordenadas para los activos públicos de informe."""
    parts = Path(canonical_relative).parts
    if not parts:
        return []
    root = parts[0]
    if root == "data":
        if metadata_asset is None:
            return [f"{canonical_relative}: dato público fuera de la lista blanca"]
        if len(parts) != 3 or parts[:2] != ("data", "metadata"):
            return [f"{canonical_relative}: ruta de metadatos no conforme"]
        return []
    if root not in {"tables", "figures", "multiqc"}:
        return []
    if len(parts) != 3:
        return [f"{canonical_relative}: activo sin carpeta de capítulo"]
    directory_match = CHAPTER_DIRECTORY_PATTERN.fullmatch(parts[1])
    if directory_match is None:
        return [f"{canonical_relative}: carpeta de capítulo no conforme"]
    patterns = {
        "tables": TABLE_FILENAME_PATTERN,
        "figures": FIGURE_FILENAME_PATTERN,
        "multiqc": MULTIQC_FILENAME_PATTERN,
    }
    filename_match = patterns[root].fullmatch(parts[2])
    if filename_match is None:
        return [f"{canonical_relative}: nombre de activo no conforme"]
    if int(directory_match["chapter"]) != int(filename_match["chapter"]):
        return [f"{canonical_relative}: capítulo de carpeta y nombre no coincide"]
    return []


def check_table_header(path: Path, restricted: set[str]) -> list[str]:
    if path.suffix.lower() not in {".tsv", ".csv"}:
        return []
    delimiter = "\t" if path.suffix.lower() == ".tsv" else ","
    with path.open(encoding="utf-8-sig", newline="") as handle:
        header = next(csv.reader(handle, delimiter=delimiter), [])
    found = restricted.intersection(item.strip().lower() for item in header)
    return [
        f"{repo_relative(path)}: cabecera restringida {item}" for item in sorted(found)
    ]


def check_text(path: Path) -> list[str]:
    if path.suffix.lower() not in {".tsv", ".csv", ".txt", ".html", ".json", ".qmd", ".md"}:
        return []
    content = path.read_text(encoding="utf-8", errors="replace")
    if PATH_PATTERN.search(content):
        return [f"{repo_relative(path)}: contiene una ruta absoluta restringida"]
    return []


def check_workbook(path: Path) -> list[str]:
    """Revisa las partes XML de un XLSX autorizado sin exponer su contenido."""
    try:
        with zipfile.ZipFile(path) as workbook:
            members = workbook.namelist()
            if any(member.lower().endswith("vbaproject.bin") for member in members):
                return [f"{repo_relative(path)}: contiene macros no publicables"]
            text_members = [
                member
                for member in members
                if member.lower().endswith((".xml", ".rels", ".txt"))
            ]
            if not text_members:
                return [f"{repo_relative(path)}: no tiene una estructura XLSX válida"]
            for member in text_members:
                content = workbook.read(member).decode("utf-8", errors="replace")
                if PATH_PATTERN.search(content):
                    return [f"{repo_relative(path)}: contiene una ruta absoluta restringida"]
    except zipfile.BadZipFile:
        return [f"{repo_relative(path)}: no es un XLSX válido"]
    return []


def check_metadata_include(path: Path, table: dict) -> list[str]:
    """Valida que el include generado sea estático, escapado y paginable."""
    if not path.exists():
        return []
    content = path.read_text(encoding="utf-8", errors="replace")
    errors = check_text(path)
    if re.search(r"<script\b", content, flags=re.IGNORECASE):
        errors.append(f"{repo_relative(path)}: un include generado no puede contener scripts")
    if "data-table-pagination" not in content:
        errors.append(f"{repo_relative(path)}: falta data-table-pagination")
    expected_id = str(table["table_id"])
    table_ids = re.findall(r"<table\b[^>]*\bid=\"([^\"]+)\"", content, flags=re.IGNORECASE)
    if table_ids != [expected_id]:
        errors.append(f"{repo_relative(path)}: el identificador de tabla no coincide")
    if "data-table-label=" not in content:
        errors.append(f"{repo_relative(path)}: falta la etiqueta accesible de tabla")
    return errors


def iter_source_text_files() -> list[Path]:
    paths = [REPO_ROOT / "index.qmd"]
    for directory in SOURCE_TEXT_DIRS:
        if directory.is_dir():
            paths.extend(sorted(directory.rglob("*.qmd")))
    return [path for path in paths if path.is_file()]


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--include-docs",
        action="store_true",
        help="Incluye HTML generado en docs/ en la comprobación de rutas.",
    )
    args = parser.parse_args()
    try:
        config = load_config()
        metadata_by_destination = configured_metadata_assets(config)
    except (OSError, ValueError, KeyError, json.JSONDecodeError, ValidationError) as error:
        print(f"[validate] ERROR de configuración: {error}", file=sys.stderr)
        return 1

    restricted_headers = {item.lower() for item in config["restricted_table_headers"]}
    errors: list[str] = []
    roots = [REPO_ROOT / name for name in PUBLIC_ASSET_DIRS]
    roots.append(INCLUDE_ROOT)
    if args.include_docs:
        roots.append(REPO_ROOT / "docs")

    for root in roots:
        if not root.exists():
            continue
        for path in root.rglob("*"):
            if not path.is_file():
                continue
            relative = repo_relative(path)
            canonical_relative = (
                relative.removeprefix("docs/") if relative.startswith("docs/") else relative
            )
            metadata_asset = metadata_by_destination.get(canonical_relative)
            errors.extend(check_report_asset_path(canonical_relative, metadata_asset))
            in_metadata_root = canonical_relative.startswith("data/metadata/")
            if in_metadata_root and metadata_asset is None:
                errors.append(f"{relative}: activo de metadatos fuera de la lista blanca")
            extension_is_allowed_metadata = (
                metadata_asset is not None
                and metadata_asset["format"] == "xlsx"
                and path.suffix.lower() == ".xlsx"
            )
            if contains_blocked_extension(path, config["blocked_extensions"]) and not extension_is_allowed_metadata:
                errors.append(f"{relative}: extensión no publicable")
            if path.suffix.lower() in {".tsv", ".csv"} and metadata_asset is None:
                errors.extend(check_table_header(path, restricted_headers))
            errors.extend(check_text(path))
            if path.suffix.lower() == ".xlsx" and extension_is_allowed_metadata:
                errors.extend(check_workbook(path))

    for asset in metadata_by_destination.values():
        table = asset.get("table")
        if isinstance(table, dict):
            include = REPO_ROOT / table["include_destination"]
            errors.extend(check_metadata_include(include, table))
    for path in iter_source_text_files():
        errors.extend(check_text(path))

    if errors:
        print("[validate] Se han detectado activos no publicables:", file=sys.stderr)
        print("\n".join(f"- {item}" for item in errors), file=sys.stderr)
        return 1
    print("[validate] activos públicos validados")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
