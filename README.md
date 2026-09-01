# Proyecto Carpio

Libro Quarto del análisis de microbiota en biopsias digestivas mediante
amplicones 16S rRNA V3–V4. El repositorio contiene una versión pública,
curada y reproducible del informe; incluye los metadatos técnicos y clínicos
individuales cuya publicación ha sido autorizada expresamente para CARPIO, pero
no contiene datos crudos de secuenciación.

## Estado actual

La versión actual documenta el contexto, el diseño experimental, el inventario
técnico paginado de las 198 bibliotecas, la auditoría de entradas, el control
de calidad, el diagnóstico y recorte de primers, y la comparación de
profundidad de las ocho biopsias repetidas. Las etapas de DADA2, ASV,
taxonomía, decontaminación y análisis clínico se incorporarán solo cuando sus
resultados estén disponibles y se solicite expresamente una actualización.

## Regla operativa

Este libro **no se actualiza automáticamente** cuando cambia el proyecto
analítico. La secuencia acordada es:

1. Actualizar activos y capítulos únicamente bajo una petición explícita.
2. Revisar el render local completo.
3. Hacer commit y `push` únicamente bajo una petición explícita de publicar.

## Construcción manual

```bash
# Renderiza el libro completo con el contenido ya presente en este repositorio.
# Es obligatorio antes de un commit destinado a publicación.
scripts/build_report.sh

# Revisión rápida de un único capítulo durante la edición local.
# No sustituye al render completo previo a publicar.
scripts/build_report.sh --chapter chapters/04_control_calidad_preprocesamiento.qmd

# Exporta activos curados desde el análisis y renderiza. Reutiliza los MultiQC
# ya validados; es la opción normal si no han cambiado los FastQC.
CARPIO_ANALYSIS_DIR=/ruta/a/CARPIO2 scripts/build_report.sh --export

# Reconstruye los MultiQC saneados solo si cambiaron los FastQC de origen.
CARPIO_ANALYSIS_DIR=/ruta/a/CARPIO2 scripts/build_report.sh --export --rebuild-multiqc

# Exporta sin renderizar.
CARPIO_ANALYSIS_DIR=/ruta/a/CARPIO2 scripts/build_report.sh --export-only
```

`docs/` es el directorio de salida para GitHub Pages. El workflow de GitHub
Actions valida y despliega el sitio estático ya renderizado; no vuelve a
renderizarlo ni sincroniza activos desde el proyecto analítico.

## Política de publicación

- Se publican figuras, tablas y MultiQC saneado necesarios para el informe.
- Los códigos técnicos de muestra `01-xxx` pueden aparecer en activos
  aprobados.
- Por autorización expresa registrada el 2026-09-01, se publican los
  metadatos técnicos y clínicos individuales de CARPIO, incluidos los códigos
  de muestra no trazables a pacientes dentro del alcance de este proyecto.
- No se publican FASTQ, objetos pesados ni rutas absolutas o internas de
  ejecución.
- Las asociaciones clínicas se mostrarán preferentemente como resultados
  agregados para facilitar su interpretación.

## Convención de activos

Las tablas y figuras se organizan por capítulo y se nombran como
`Table-N.M-identificador.ext` y `Fig-N.M-identificador.ext`. Las tablas navegables de metadatos se corresponden con las Tablas 2.5–2.7 y sus formatos descargables comparten el prefijo `Table-2.N-` en `tables/02_diseno_experimental/`. La política y sus excepciones se describen en
[ASSET_CONVENTIONS.md](ASSET_CONVENTIONS.md) y se comprueban automáticamente
antes de cada render y despliegue.

## Estructura

```text
.
├── .github/workflows/  despliegue de GitHub Pages tras push a main
├── assets/             recursos locales de presentación e interactividad
├── appendices/         reproducibilidad y disponibilidad de datos
├── chapters/           capítulos y fragmentos HTML curados del libro
├── config/             lista permitida de activos y reglas de exportación
├── figures/            figuras curadas, agrupadas por capítulo
├── manifests/          trazabilidad de las exportaciones y builds
├── multiqc/            informes MultiQC saneados, agrupados por capítulo
├── scripts/            exportación, validación y render manual
├── tables/             tablas y datos de apoyo, agrupados por capítulo
└── docs/               sitio estático renderizado
```

La vista se ha generado con `find` porque `tree` no está disponible en el
entorno de trabajo. `tables/02_diseno_experimental/` contiene las Tablas 2.5–2.7 y sus cinco archivos descargables de metadatos explícitamente autorizados; los FASTQ y otros datos no públicos permanecen en el proyecto analítico.

## Licencias

El código y la configuración se distribuyen bajo [MIT](LICENSE). El contenido
del informe se distribuye bajo [CC BY 4.0](LICENSE-CONTENT.md), salvo que una
figura o fuente indique otra condición.
