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
    arguments = parser.parse_args()

    try:
        config = load_config()
        analysis_root = require_analysis_root(config["analysis_dir_env"])
        rows = [
            copy_asset(asset, analysis_root, config, arguments.dry_run)
            for asset in config["allowed_assets"]
        ]
        multiqc_command = shlex.split(arguments.multiqc_command)
        if not multiqc_command:
            raise ExportError("El comando de MultiQC está vacío.")
        rows.extend(
            build_multiqc_report(
                report, analysis_root, multiqc_command, arguments.dry_run
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
