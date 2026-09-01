# Convención de activos del informe

## Alcance

Esta política organiza exclusivamente la capa pública del libro Quarto. El
proyecto analítico conserva sus propias rutas por etapa; no se replica esa
estructura en este repositorio.

`index.qmd` es una portada/resumen no numerada. El primer capítulo numerado es
`chapters/01_introduccion.qmd`, por lo que los números de los nombres de archivo
coinciden con los números que muestra el libro.

## Tablas y figuras del informe

Quarto asigna de forma automática las referencias cruzadas por capítulo. Las
etiquetas se mantienen semánticas, por ejemplo `#tbl-preprocessing-summary` o
`#fig-repeated-depth`, para que no haya que reescribirlas si cambia el orden.

Los activos externos directamente asociados a una referencia del manuscrito se
organizan por capítulo:

```text
tables/04_control_calidad_preprocesamiento/
  Table-4.1-profundidad-bibliotecas-crudas.tsv
  Table-4.3-profundidad-biopsias-repetidas.tsv
figures/04_control_calidad_preprocesamiento/
  Fig-4.1-profundidad-biopsias-repetidas.png
  Fig-4.1-profundidad-biopsias-repetidas.pdf
```

La forma obligatoria es `Table-N.M-identificador.ext` o
`Fig-N.M-identificador.ext`, donde `N` es el capítulo mostrado en el libro y
`M` el orden de tabla o figura dentro de ese capítulo. Se usan guiones,
minúsculas ASCII en el identificador y extensiones convencionales. Los formatos
alternativos de una misma figura comparten exactamente el mismo prefijo.

Los TSV y CSV exportados se normalizan a finales de línea LF, de modo que el
checksum del manifiesto coincide con el activo versionado y descargable.

Un activo de detalle puede compartir la referencia `N.M` de la tabla que
sustenta; se diferencia mediante un identificador final, por ejemplo
`-crudas`, `-recortadas` o `-resumen`. Las tablas redactadas directamente en un
archivo `.qmd` no se duplican como archivos de datos: la fuente Quarto es su
única fuente canónica.

## Datos descargables

Los TSV y libros Excel completos de metadatos no son tablas científicas
numeradas. Se guardan en `data/metadata/` con sus nombres canónicos autorizados:

```text
CARPIO_technical_metadata.tsv
CARPIO_technical_metadata.xlsx
CARPIO_clinical_metadata.tsv
CARPIO_clinical_metadata.xlsx
CARPIO_analysis_metadata.tsv
```

Esta excepción evita renombrar o duplicar datos de descarga para forzar una
numeración de informe. La lista blanca de publicación sigue siendo restrictiva:
solo esos cinco ficheros pueden existir bajo `data/metadata/`.

## Control y actualización

Cada activo exportable declara su ruta en `config/publication_assets.json`; esa
ruta codifica el capítulo y el número visible cuando corresponde. El manifiesto
conserva la ruta, checksum y descripción. El validador comprueba tanto la
seguridad de publicación como las rutas y los nombres de esta política.

No se emplean directorios como `00_design`, `00_metadata` o
`01_preprocessing` en la capa pública. Cualquier nuevo activo debe añadirse a
la configuración, al capítulo correspondiente y al manifiesto mediante el
exportador manual.
