#!/usr/bin/env bash
set -euo pipefail

usage() {
  cat <<'USAGE'
Uso: scripts/build_report.sh [--export] [--export-only] [--no-render]

El comportamiento por defecto renderiza únicamente los activos ya presentes en
este repositorio. La exportación desde el análisis requiere --export (o
--export-only) y CARPIO_ANALYSIS_DIR; úsela solo tras una instrucción explícita
de actualizar el informe Quarto.

Opciones:
  --export        Exporta activos curados y después renderiza.
  --export-only   Exporta activos curados y termina sin renderizar.
  --no-render     No renderiza (útil junto con --export).
USAGE
}

export_assets=0
export_only=0
render=1

while [ "$#" -gt 0 ]; do
  case "$1" in
    --export) export_assets=1 ;;
    --export-only) export_assets=1; export_only=1 ;;
    --no-render) render=0 ;;
    -h|--help) usage; exit 0 ;;
    *) echo "Opción desconocida: $1" >&2; usage >&2; exit 2 ;;
  esac
  shift
done

if [ "$export_only" -eq 1 ]; then
  render=0
fi

REPO_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd -P)"
cd "$REPO_DIR"
mkdir -p manifests/logs
LOG_FILE="manifests/logs/build_report_$(date +%Y%m%d_%H%M%S).log"

{
  echo "[build] started=$(date -Is)"
  echo "[build] mode=$([ "$export_assets" -eq 1 ] && echo export || echo render-only)"

  if [ "$export_assets" -eq 1 ]; then
    : "${CARPIO_ANALYSIS_DIR:?Defina CARPIO_ANALYSIS_DIR para exportar activos curados.}"
    echo "[build] exportación manual de activos permitidos"
    python3 scripts/export_public_assets.py
  else
    echo "[build] no se exportan activos; se usan los ya versionados"
  fi

  echo "[build] validando activos públicos"
  python3 scripts/validate_public_assets.py

  if [ "$render" -eq 1 ]; then
    echo "[build] renderizando Quarto"
    quarto render
    echo "[build] validando HTML generado"
    python3 scripts/validate_public_assets.py --include-docs
  else
    echo "[build] render omitido"
  fi
  echo "[build] finished=$(date -Is)"
} 2>&1 | tee "$LOG_FILE"
