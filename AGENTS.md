# Proyecto Carpio — instrucciones del repositorio

## Propósito y autoridad

Este repositorio es la capa de publicación Quarto del análisis de microbiota
CARPIO2. El proyecto analítico autoritativo se configura con la variable de
entorno `CARPIO_ANALYSIS_DIR`; este repositorio no recalcula DADA2, taxonomía,
decontaminación ni análisis clínicos.

## Actualización manual obligatoria

- No ejecutar exportación, render ni `git push` automáticamente.
- Actualizar activos únicamente tras una instrucción explícita de actualizar el
  informe Quarto.
- Publicar en GitHub Pages únicamente tras una instrucción explícita de
  publicar o hacer `push`.
- El workflow de GitHub Actions solo renderiza los activos ya presentes en el
  repositorio; nunca accede al proyecto analítico.

## Política de datos públicos

- No incluir FASTQ, BAM, objetos R, metadatos clínicos por individuo,
  identificadores de paciente, fechas clínicas ni rutas internas.
- Se permiten figuras y tablas curadas con los códigos técnicos de muestra
  aprobados (`01-xxx`).
- Las asociaciones clínicas públicas se presentan únicamente de forma
  agregada.
- Todos los activos se incorporan mediante `scripts/export_public_assets.py`
  y se validan con `scripts/validate_public_assets.py`.

## Estructura y renderizado

- Las fuentes Quarto viven en `index.qmd`, `chapters/` y `appendices/`.
- Los activos públicos viven en `figures/`, `tables/` y `multiqc/`.
- `docs/` es la salida estática para GitHub Pages y futura migración a
  Cloudflare Pages.
- `config/publication_assets.json` es la lista permitida de activos externos.
- Los logs y manifiestos viven en `manifests/`.

## Comandos manuales

```bash
# Exportar activos curados y renderizar: solo bajo petición explícita.
CARPIO_ANALYSIS_DIR=/ruta/a/CARPIO2 scripts/build_report.sh --export

# Renderizar solo los activos ya exportados.
scripts/build_report.sh

# Exportar sin renderizar.
CARPIO_ANALYSIS_DIR=/ruta/a/CARPIO2 scripts/build_report.sh --export-only
```

Antes de publicar, revisar el sitio local y el manifiesto. No crear remotos ni
hacer `push` sin una indicación inequívoca de la persona responsable.
