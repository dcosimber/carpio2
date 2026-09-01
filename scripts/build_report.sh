#!/usr/bin/env bash
set -euo pipefail

usage() {
  cat <<USAGE
Uso: scripts/build_report.sh [--export] [--rebuild-multiqc] [--export-only] [--chapter <archivo.qmd>] [--no-render]

El comportamiento por defecto renderiza únicamente los activos ya presentes en
este repositorio. La exportación desde el análisis requiere --export (o
--export-only) y CARPIO_ANALYSIS_DIR; úsela solo tras una instrucción explícita
de actualizar el informe Quarto.

Opciones:
  --export              Exporta activos curados y después renderiza; reutiliza MultiQC ya validado.
  --rebuild-multiqc     Regenera MultiQC; usar solo si cambiaron los FastQC de origen.
  --export-only         Exporta activos curados y termina sin renderizar.
  --chapter <archivo>   Renderiza solo un capítulo para revisión local.
  --no-render           No renderiza (útil junto con --export).
USAGE
}

export_assets=0
export_only=0
render=1
rebuild_multiqc=0
chapter=""

while [ "$#" -gt 0 ]; do
  case "$1" in
    --export) export_assets=1 ;;
    --rebuild-multiqc) rebuild_multiqc=1 ;;
    --export-only) export_assets=1; export_only=1 ;;
    --chapter)
      shift
      [ "$#" -gt 0 ] || { echo "--chapter requiere una ruta .qmd" >&2; exit 2; }
      chapter="$1"
      ;;
    --no-render) render=0 ;;
    -h|--help) usage; exit 0 ;;
    *) echo "Opción desconocida: $1" >&2; usage >&2; exit 2 ;;
  esac
  shift
done

if [ "$export_only" -eq 1 ]; then
  render=0
fi

if [ "$rebuild_multiqc" -eq 1 ] && [ "$export_assets" -ne 1 ]; then
  echo "--rebuild-multiqc requiere --export" >&2
  exit 2
fi

if [ -n "$chapter" ]; then
  case "$chapter" in
    index.qmd|chapters/*.qmd|appendices/*.qmd) ;;
    *) echo "--chapter debe apuntar a index.qmd, chapters/*.qmd o appendices/*.qmd" >&2; exit 2 ;;
  esac
  [ "$export_only" -eq 0 ] || { echo "--chapter no es compatible con --export-only" >&2; exit 2; }
fi

REPO_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd -P)"
cd "$REPO_DIR"
mkdir -p manifests/logs
LOG_FILE="manifests/logs/build_report_$(date +%Y%m%d_%H%M%S).log"

{
  started_epoch="$(date +%s)"
  echo "[build] started=$(date -Is)"
  echo "[build] mode=$([ "$export_assets" -eq 1 ] && echo export || echo render-only)"

  if [ "$export_assets" -eq 1 ]; then
    : "${CARPIO_ANALYSIS_DIR:?Defina CARPIO_ANALYSIS_DIR para exportar activos curados.}"
    if [ "$rebuild_multiqc" -eq 1 ]; then
      echo "[build] exportación manual y regeneración explícita de MultiQC"
      python3 scripts/export_public_assets.py
    else
      echo "[build] exportación manual; se reutilizan los MultiQC ya validados"
      python3 scripts/export_public_assets.py --skip-multiqc
    fi
  else
    echo "[build] no se exportan activos; se usan los ya versionados"
  fi

  echo "[build] validando activos públicos"
  python3 scripts/validate_public_assets.py

  if [ "$render" -eq 1 ]; then
    if [ -n "$chapter" ]; then
      echo "[build] renderizando capítulo para revisión local: $chapter"
      quarto render "$chapter"
    else
      echo "[build] renderizando libro Quarto completo"
      quarto render
    fi
    echo "[build] validando HTML generado"
    python3 scripts/validate_public_assets.py --include-docs
  else
    echo "[build] render omitido"
  fi
  echo "[build] elapsed_seconds=$(( $(date +%s) - started_epoch ))"
  echo "[build] finished=$(date -Is)"
} 2>&1 | tee "$LOG_FILE"
