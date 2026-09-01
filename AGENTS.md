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
- El workflow de GitHub Actions despliega el sitio estático validado presente
  en el repositorio; nunca accede al proyecto analítico ni vuelve a renderizar.

## Política de datos públicos

- Por autorización expresa de la persona responsable del proyecto, registrada
  el 2026-09-01, pueden incorporarse al repositorio los metadatos técnicos y
  clínicos individuales de CARPIO, incluidos sus libros Excel, tablas TSV y
  los códigos de muestra. En el alcance de este proyecto, esos códigos no son
  trazables a pacientes.
- Esta autorización es específica de CARPIO y no se extrapola a otros
  proyectos ni a fuentes de datos nuevas sin una indicación explícita.
- No incluir FASTQ, BAM, CRAM, SAM, objetos R, archivos comprimidos de datos
  crudos ni rutas absolutas o internas de ejecución.
- Las asociaciones clínicas se presentarán preferentemente de forma agregada
  por claridad analítica; esa elección no limita la disponibilidad autorizada
  de los metadatos de este proyecto.
- Todos los activos se incorporan mediante `scripts/export_public_assets.py`
  y se validan con `scripts/validate_public_assets.py`.

## Estructura y renderizado

- Las fuentes Quarto viven en `index.qmd`, `chapters/` y `appendices/`.
- Los datos públicos descargables expresamente autorizados viven en `data/`.
- Los activos del informe viven en `figures/`, `tables/` y `multiqc/`.
- `docs/` es la salida estática para GitHub Pages y futura migración a
  Cloudflare Pages.
- `config/publication_assets.json` es la lista permitida de activos externos.
- Los logs y manifiestos viven en `manifests/`.

## Convención permanente de tablas, figuras y datos

- `index.qmd` es una portada/resumen sin número. Por tanto,
  `chapters/01_*` es el capítulo 1, `chapters/02_*` el capítulo 2, etc.
- Las tablas y figuras citables se numeran automáticamente con Quarto por
  capítulo (`Tabla N.M` y `Figura N.M`). Sus etiquetas son semánticas
  (`#tbl-*`, `#fig-*`), nunca codifican números que Quarto ya gestiona.
- Todo activo externo asociado a una tabla o figura se guarda en una carpeta
  de capítulo: `tables/NN_nombre_capitulo/` o
  `figures/NN_nombre_capitulo/`. Sus nombres siguen
  `Table-N.M-identificador.ext` y `Fig-N.M-identificador.ext`, con rutas y
  slugs ASCII. Las versiones PNG/PDF de una misma figura comparten prefijo.
- Los ficheros de detalle que sustentan la misma tabla pueden compartir `N.M`
  y se distinguen por el identificador; no se duplican tablas escritas de forma
  nativa en los capítulos solo para crear un TSV.
- Los libros y TSV completos de metadatos son datos descargables, no tablas
  científicas adicionales. Se conservan con su nombre canónico autorizado en
  `data/metadata/` (`CARPIO_*_metadata.*`) y no consumen un número de tabla.
- No usar directorios genéricos o heredados de etapas analíticas como `00_*` o
  `01_preprocessing` en la capa pública. La validación de activos aplica esta
  convención y bloquea rutas no conformes.
- La política legible para colaboradores se conserva en
  `ASSET_CONVENTIONS.md`; `config/publication_assets.json` y su manifiesto
  contienen la trazabilidad por activo.

## Comandos manuales

```bash
# Exportar activos curados y renderizar: solo bajo petición explícita.
# Reutiliza los MultiQC ya validados.
CARPIO_ANALYSIS_DIR=/ruta/a/CARPIO2 scripts/build_report.sh --export

# Regenerar MultiQC solo cuando hayan cambiado sus FastQC de origen.
CARPIO_ANALYSIS_DIR=/ruta/a/CARPIO2 scripts/build_report.sh --export --rebuild-multiqc

# Renderizar solo los activos ya exportados; este es el render completo previo
# a un commit o despliegue.
scripts/build_report.sh

# Revisión rápida de un único capítulo durante la edición local. No sustituye
# al render completo previo a publicar.
scripts/build_report.sh --chapter chapters/04_control_calidad_preprocesamiento.qmd

# Exportar sin renderizar.
CARPIO_ANALYSIS_DIR=/ruta/a/CARPIO2 scripts/build_report.sh --export-only
```

Antes de publicar, revisar el sitio local, el manifiesto y el render completo.
No crear remotos ni hacer `push` sin una indicación inequívoca de la persona
responsable.
