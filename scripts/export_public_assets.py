#!/usr/bin/env python3
"""Exporta activos explícitamente autorizados al libro Quarto público.

Este script es intencionadamente conservador: solo copia las rutas presentes en
config/publication_assets.json y nunca publica inputs de secuenciación,
metadatos clínicos individuales ni objetos de análisis. Debe ejecutarse de
forma manual con CARPIO_ANALYSIS_DIR definido.
"""

from __future__ import annotations

import argparse
import csv
import html
import hashlib
import json
import os
import re
import shlex
import shutil
import subprocess
import sys
import tempfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Iterable


REPO_ROOT = Path(__file__).resolve().parents[1]
CONFIG_PATH = REPO_ROOT / "config" / "publication_assets.json"
MANIFEST_PATH = REPO_ROOT / "manifests" / "public_asset_manifest.tsv"
ALLOWED_PUBLIC_ROOTS = ("tables", "figures", "multiqc")
ALLOWED_INCLUDE_ROOT = "chapters/includes/"
ABSOLUTE_PATH_PATTERN = re.compile(r"(?:^|[\\\"'>( ])/(?:mnt|home|tmp|var/tmp|Users|private)(?:/|$)")


class ExportError(RuntimeError):
    """A controlled failure that prevents an unsafe export."""


def sha256sum(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def load_config() -> dict:
    with CONFIG_PATH.open(encoding="utf-8") as handle:
        return json.load(handle)


def require_analysis_root(variable: str) -> Path:
    value = os.environ.get(variable)
    if not value:
        raise ExportError(
            f"Falta la variable {variable}. Indique la raíz del proyecto analítico "
            "solo al ejecutar una actualización manual."
        )
    root = Path(value).resolve()
    if not root.is_dir():
        raise ExportError(f"{variable} no apunta a un directorio legible.")
    return root


def is_within(child: Path, parent: Path) -> bool:
    try:
        child.relative_to(parent)
    except ValueError:
        return False
    return True


def resolve_source(analysis_root: Path, relative_source: str) -> Path:
    source = (analysis_root / relative_source).resolve()
    if not is_within(source, analysis_root):
        raise ExportError("Una ruta de origen sale de la raíz analítica permitida.")
    if not source.is_file():
        raise ExportError(f"No existe el activo autorizado: {relative_source}")
    return source


def resolve_destination(relative_destination: str) -> Path:
    destination = (REPO_ROOT / relative_destination).resolve()
    if not is_within(destination, REPO_ROOT):
        raise ExportError("Una ruta de destino sale del repositorio.")
    if not relative_destination.startswith(ALLOWED_PUBLIC_ROOTS):
        raise ExportError("El destino no pertenece a una carpeta pública autorizada.")
    return destination


def resolve_include_destination(relative_destination: str) -> Path:
    """Resolve a generated Quarto include without allowing arbitrary writes."""
    destination = (REPO_ROOT / relative_destination).resolve()
    if not is_within(destination, REPO_ROOT):
        raise ExportError("Una ruta de include sale del repositorio.")
    if not relative_destination.startswith(ALLOWED_INCLUDE_ROOT):
        raise ExportError("El include no pertenece a chapters/includes/.")
    return destination


def validate_extension(path: Path, blocked_extensions: Iterable[str]) -> None:
    lower_name = path.name.lower()
    if any(lower_name.endswith(extension) for extension in blocked_extensions):
        raise ExportError(f"Extensión no publicable: {path.name}")


def validate_table_headers(path: Path, restricted_headers: Iterable[str]) -> None:
    if path.suffix.lower() not in {".tsv", ".csv"}:
        return
    delimiter = "\t" if path.suffix.lower() == ".tsv" else ","
    with path.open(encoding="utf-8", newline="") as handle:
        reader = csv.reader(handle, delimiter=delimiter)
        header = next(reader, [])
    normalized = {item.strip().lower() for item in header}
    restricted = {item.lower() for item in restricted_headers}
    overlap = normalized.intersection(restricted)
    if overlap:
        raise ExportError(
            "La tabla contiene cabeceras restringidas: " + ", ".join(sorted(overlap))
        )


def validate_text_has_no_internal_paths(path: Path) -> None:
    if path.suffix.lower() not in {".tsv", ".csv", ".txt", ".html", ".json"}:
        return
    text = path.read_text(encoding="utf-8", errors="replace")
    if ABSOLUTE_PATH_PATTERN.search(text):
        raise ExportError(f"El activo contiene una ruta absoluta no publicable: {path.name}")


def copy_asset(
    asset: dict,
    analysis_root: Path,
    config: dict,
    dry_run: bool,
) -> dict:
    source = resolve_source(analysis_root, asset["source"])
    destination = resolve_destination(asset["destination"])
    validate_extension(destination, config["blocked_extensions"])
    validate_table_headers(source, config["restricted_table_headers"])
    validate_text_has_no_internal_paths(source)
    if not dry_run:
        destination.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(source, destination)
        validate_table_headers(destination, config["restricted_table_headers"])
        validate_text_has_no_internal_paths(destination)
    return {
        "asset_id": asset["id"],
        "source_relative": asset["source"],
        "destination_relative": asset["destination"],
        "description": asset["description"],
        "sha256": sha256sum(source) if dry_run else sha256sum(destination),
        "kind": "file",
    }


def public_value(value: str | None, source_column: str, value_maps: dict) -> str:
    """Normalise missing values and apply only configured public labels."""
    if value is None or value.strip() in {"", "NA", "NaN", "NULL"}:
        return "—"
    return value_maps.get(source_column, {}).get(value, value)


def render_sample_table_html(fields: list[dict], rows: list[dict], expected_rows: int) -> str:
    """Build an escaped, non-executable HTML table for Quarto inclusion."""
    headers = "".join(
        f'<th scope="col">{html.escape(field["label"])}</th>' for field in fields
    )
    body = "\n".join(
        "<tr>"
        + "".join(
            f'<td>{html.escape(row[field["output"]])}</td>' for field in fields
        )
        + "</tr>"
        for row in rows
    )
    return (
        '<div class="sample-table-scroll" data-sample-table-pagination '
        'data-page-size="10" role="region" '
        'aria-label="Tabla técnica completa de bibliotecas" tabindex="0">\n'
        '<table id="sample-inventory" class="sample-inventory" data-page-size="10">\n'
        f'<caption>Inventario técnico de las {expected_rows} bibliotecas paired-end incluidas en el análisis.</caption>\n'
        f"<thead><tr>{headers}</tr></thead>\n"
        f"<tbody>\n{body}\n</tbody>\n"
        "</table>\n"
        "</div>\n"
    )


def build_curated_tsv_asset(
    asset: dict,
    analysis_root: Path,
    config: dict,
    dry_run: bool,
) -> dict:
    """Export an allowlisted subset of a TSV that may contain private fields."""
    source = resolve_source(analysis_root, asset["source"])
    destination = resolve_destination(asset["destination"])
    include_destination = resolve_include_destination(asset["include_destination"])
    validate_extension(destination, config["blocked_extensions"])

    fields = asset["fields"]
    source_columns = [field["source"] for field in fields]
    output_columns = [field["output"] for field in fields]
    restricted = {item.lower() for item in config["restricted_table_headers"]}
    if restricted.intersection(column.lower() for column in source_columns):
        raise ExportError("La curación solicitó una columna restringida.")
    if len(output_columns) != len(set(output_columns)):
        raise ExportError("La tabla curada tiene columnas de salida duplicadas.")

    with source.open(encoding="utf-8", newline="") as handle:
        reader = csv.DictReader(handle, delimiter="\t")
        if reader.fieldnames is None:
            raise ExportError("La tabla fuente no contiene cabecera.")
        missing = set(source_columns).difference(reader.fieldnames)
        if missing:
            raise ExportError(
                "Faltan columnas autorizadas en la tabla fuente: "
                + ", ".join(sorted(missing))
            )
        rows = [
            {
                field["output"]: public_value(
                    row[field["source"]], field["source"], asset.get("value_maps", {})
                )
                for field in fields
            }
            for row in reader
        ]

    expected_rows = int(asset["expected_rows"])
    if len(rows) != expected_rows:
        raise ExportError(
            f"La tabla curada tiene {len(rows)} filas; se esperaban {expected_rows}."
        )
    if not dry_run:
        destination.parent.mkdir(parents=True, exist_ok=True)
        with destination.open("w", encoding="utf-8", newline="") as handle:
            writer = csv.DictWriter(
                handle,
                fieldnames=output_columns,
                delimiter="\t",
                lineterminator="\n",
            )
            writer.writeheader()
            writer.writerows(rows)
        include_destination.parent.mkdir(parents=True, exist_ok=True)
        include_destination.write_text(
            render_sample_table_html(fields, rows, expected_rows), encoding="utf-8"
        )
        validate_table_headers(destination, config["restricted_table_headers"])
        validate_text_has_no_internal_paths(destination)
        validate_text_has_no_internal_paths(include_destination)

    return {
        "asset_id": asset["id"],
        "source_relative": asset["source"],
        "destination_relative": asset["destination"],
        "description": asset["description"],
        "sha256": sha256sum(source) if dry_run else sha256sum(destination),
        "kind": "curated_tsv",
    }


def copy_fastqc_archives(analysis_root: Path, relative_dirs: list[str], stage: Path) -> int:
    copied = 0
    seen_names: set[str] = set()
    for relative_directory in relative_dirs:
        directory = (analysis_root / relative_directory).resolve()
        if not is_within(directory, analysis_root) or not directory.is_dir():
            raise ExportError(f"No existe el directorio FastQC autorizado: {relative_directory}")
        for archive in sorted(directory.rglob("*_fastqc.zip")):
            if archive.name in seen_names:
                raise ExportError(f"Nombre duplicado de informe FastQC: {archive.name}")
            seen_names.add(archive.name)
            shutil.copy2(archive, stage / archive.name)
            copied += 1
    if copied == 0:
        raise ExportError("No se encontraron archivos *_fastqc.zip para generar MultiQC.")
    return copied


def sanitize_multiqc_html(report: Path, stage: Path, output: Path, analysis_root: Path) -> None:
    content = report.read_text(encoding="utf-8", errors="replace")
    replacements = {
        str(stage): "[ruta temporal omitida]",
        str(output): "[salida temporal omitida]",
        str(analysis_root): "[ruta de análisis omitida]",
    }
    for original, replacement in replacements.items():
        content = content.replace(original, replacement)
        content = content.replace(original.replace("\\", "/"), replacement)
    report.write_text(content, encoding="utf-8")
    validate_text_has_no_internal_paths(report)


def build_multiqc_report(
    report_config: dict,
    analysis_root: Path,
    multiqc_command: list[str],
    dry_run: bool,
) -> dict:
    destination = resolve_destination(report_config["destination"])
    validate_extension(destination, [".zip", ".fastq", ".fastq.gz", ".fq", ".fq.gz"])
    if dry_run:
        archive_count = sum(
            len(list((analysis_root / directory).glob("*_fastqc.zip")))
            for directory in report_config["input_directories"]
            if (analysis_root / directory).is_dir()
        )
        if archive_count == 0:
            raise ExportError("No hay archivos FastQC para el MultiQC solicitado.")
        return {
            "asset_id": report_config["id"],
            "source_relative": ";".join(report_config["input_directories"]),
            "destination_relative": report_config["destination"],
            "description": report_config["description"],
            "sha256": "dry-run",
            "kind": "sanitized_multiqc",
        }

    with tempfile.TemporaryDirectory(prefix="carpio2_multiqc_") as temporary:
        temporary_root = Path(temporary)
        stage = temporary_root / "fastqc"
        output = temporary_root / "multiqc"
        stage.mkdir()
        output.mkdir()
        archive_count = copy_fastqc_archives(
            analysis_root, report_config["input_directories"], stage
        )
        command = [
            *multiqc_command,
            str(stage),
            "--outdir",
            str(output),
            "--filename",
            report_config["filename"],
            "--force",
            "--no-data-dir",
            "--no-ai",
        ]
        print("[export] generating sanitized MultiQC from", archive_count, "FastQC archives")
        subprocess.run(command, check=True)
        generated = output / report_config["filename"]
        if not generated.is_file():
            raise ExportError("MultiQC no produjo el informe HTML esperado.")
        sanitize_multiqc_html(generated, stage, output, analysis_root)
        destination.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(generated, destination)
        validate_text_has_no_internal_paths(destination)

    return {
        "asset_id": report_config["id"],
        "source_relative": ";".join(report_config["input_directories"]),
        "destination_relative": report_config["destination"],
        "description": report_config["description"],
        "sha256": sha256sum(destination),
        "kind": "sanitized_multiqc",
    }


def reuse_multiqc_report(report_config: dict) -> dict:
    """Keep an already validated MultiQC report in a manual text-only update."""
    destination = resolve_destination(report_config["destination"])
    if not destination.is_file():
        raise ExportError(
            "No existe MultiQC saneado para reutilizar; ejecute una exportación completa."
        )
    validate_text_has_no_internal_paths(destination)
    return {
        "asset_id": report_config["id"],
        "source_relative": ";".join(report_config["input_directories"]),
        "destination_relative": report_config["destination"],
        "description": report_config["description"],
        "sha256": sha256sum(destination),
        "kind": "sanitized_multiqc_reused",
    }


def write_manifest(rows: list[dict], dry_run: bool) -> None:
    if dry_run:
        return
    MANIFEST_PATH.parent.mkdir(parents=True, exist_ok=True)
    timestamp = datetime.now(timezone.utc).replace(microsecond=0).isoformat()
    fieldnames = [
        "exported_at_utc",
        "asset_id",
        "kind",
        "source_relative",
        "destination_relative",
        "sha256",
        "description",
    ]
    with MANIFEST_PATH.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames, delimiter="\t")
        writer.writeheader()
        for row in rows:
            writer.writerow({"exported_at_utc": timestamp, **row})


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--dry-run", action="store_true", help="Valida la exportación sin escribir archivos."
    )
    parser.add_argument(
        "--multiqc-command",
        default=os.environ.get("CARPIO_MULTIQC_COMMAND", "conda run -n multiqc multiqc"),
        help="Comando para MultiQC; por defecto, 'conda run -n multiqc multiqc'.",
    )
    parser.add_argument(
        "--skip-multiqc",
        action="store_true",
        help=(
            "Reutiliza los MultiQC saneados ya validados; útil para una "
            "actualización manual que solo modifica texto o tablas."
        ),
    )
    arguments = parser.parse_args()

    try:
        config = load_config()
        analysis_root = require_analysis_root(config["analysis_dir_env"])
        rows = [
            copy_asset(asset, analysis_root, config, arguments.dry_run)
            for asset in config["allowed_assets"]
        ]
        rows.extend(
            build_curated_tsv_asset(asset, analysis_root, config, arguments.dry_run)
            for asset in config.get("curated_tsv_assets", [])
        )
        multiqc_command = shlex.split(arguments.multiqc_command)
        if not multiqc_command and not arguments.skip_multiqc:
            raise ExportError("El comando de MultiQC está vacío.")
        rows.extend(
            (
                reuse_multiqc_report(report)
                if arguments.skip_multiqc and not arguments.dry_run
                else build_multiqc_report(
                    report, analysis_root, multiqc_command, arguments.dry_run
                )
            )
            for report in config["multiqc_reports"]
        )
        write_manifest(rows, arguments.dry_run)
    except (ExportError, subprocess.CalledProcessError, OSError, json.JSONDecodeError) as error:
        print(f"[export] ERROR: {error}", file=sys.stderr)
        return 1

    action = "validated" if arguments.dry_run else "exported"
    print(f"[export] {action} {len(rows)} public assets")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
