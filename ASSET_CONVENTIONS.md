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

## Tablas de metadatos y archivos descargables

Las tablas navegables de metadatos se integran en el capítulo 2 como Tablas
2.5–2.7. Los activos descargables asociados comparten el prefijo de su tabla
formal y se almacenan directamente en `tables/02_diseno_experimental/`:

```text
Table-2.5-metadatos-tecnicos.tsv
Table-2.5-metadatos-tecnicos.xlsx
Table-2.6-metadatos-clinicos.tsv
Table-2.6-metadatos-clinicos.xlsx
Table-2.7-metadatos-analisis.tsv
```

Los ficheros TSV y XLSX de una misma tabla representan formatos alternativos
del mismo activo y no consumen numeración adicional. La lista blanca de
publicación sigue siendo restrictiva y solo autoriza estos cinco ficheros de
metadatos.

## Control y actualización

Cada activo exportable declara su ruta en `config/publication_assets.json`; esa
ruta codifica el capítulo y el número visible cuando corresponde. El manifiesto
conserva la ruta, checksum y descripción. El validador comprueba tanto la
seguridad de publicación como las rutas y los nombres de esta política.

No se emplean directorios como `00_design`, `00_metadata` o
`01_preprocessing` en la capa pública. Cualquier nuevo activo debe añadirse a
la configuración, al capítulo correspondiente y al manifiesto mediante el
exportador manual.
