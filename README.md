# Proyecto Carpio

Libro Quarto del análisis de microbiota en biopsias digestivas mediante
amplicones 16S rRNA V3–V4. El repositorio contiene una versión pública,
curada y reproducible del informe; no contiene datos crudos de secuenciación
ni metadatos clínicos individuales.

## Estado actual

La primera versión documenta el diseño experimental, la auditoría de entradas,
el control de calidad, el diagnóstico y recorte de primers, y la comparación
de profundidad de las ocho biopsias repetidas. Las etapas de DADA2, ASV,
taxonomía, decontaminación y análisis clínico se incorporarán solo cuando sus
resultados estén disponibles y se solicite expresamente una actualización.

## Regla operativa

Este libro **no se actualiza automáticamente** cuando cambia el proyecto
analítico. La secuencia acordada es:

1. Actualizar activos y capítulos únicamente bajo una petición explícita.
2. Revisar el render local.
3. Hacer commit y `push` únicamente bajo una petición explícita de publicar.

## Construcción manual

```bash
# Solo renderiza el contenido que ya está en este repositorio.
scripts/build_report.sh

# Exporta activos curados desde el análisis y renderiza.
CARPIO_ANALYSIS_DIR=/ruta/a/CARPIO2 scripts/build_report.sh --export

# Exporta sin renderizar.
CARPIO_ANALYSIS_DIR=/ruta/a/CARPIO2 scripts/build_report.sh --export-only
```

`docs/` es el directorio de salida para GitHub Pages. El workflow de GitHub
Actions renderiza estas fuentes al hacer `push` a `main`, pero no sincroniza
activos desde el proyecto analítico.

## Política de publicación

- Se publican figuras, tablas y MultiQC saneado necesarios para el informe.
- Los códigos técnicos de muestra `01-xxx` pueden aparecer en activos
  aprobados.
- No se publican FASTQ, objetos pesados, identificadores de paciente, fechas
  clínicas, metadatos clínicos por muestra ni rutas internas de ejecución.
- Las asociaciones clínicas se mostrarán solo como resultados agregados.

## Estructura

```text
.
├── .github/workflows/  despliegue de GitHub Pages tras push a main
├── appendices/         reproducibilidad y disponibilidad de datos
├── chapters/           capítulos del libro
├── config/             lista permitida de activos y reglas de exportación
├── figures/            figuras curadas para publicación
├── manifests/          trazabilidad de las exportaciones y builds
├── multiqc/            informes MultiQC saneados
├── scripts/            exportación, validación y render manual
├── tables/             tablas curadas para publicación
└── docs/               sitio estático renderizado (generado localmente)
```

La vista se ha generado con `find` porque `tree` no está disponible en el
entorno de trabajo. `data/` no existe en este repositorio por diseño: los FASTQ
y otros datos no públicos permanecen en el proyecto analítico.

## Licencias

El código y la configuración se distribuyen bajo [MIT](LICENSE). El contenido
del informe se distribuye bajo [CC BY 4.0](LICENSE-CONTENT.md), salvo que una
figura o fuente indique otra condición.
