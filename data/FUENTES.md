# Fuentes y metodología

La base integra tres archivos conservados en `originales/`:

- `Anexo1.NoFetal2019_CE_15-03-23.xlsx`: 244.355 registros de defunciones no fetales de 2019, hoja `No_Fetales_2019`.
- `Divipola_CE_.xlsx`: códigos y nombres territoriales, hoja `Hoja1`.
- `Anexo2.CodigosDeMuerte_CE_15-03-23.xlsx`: catálogo CIE-10, hoja `Final`.

Fuente estadística y metadatos: DANE, Estadísticas Vitales 2019, https://microdatos.dane.gov.co/index.php/catalog/696. Cifras definitivas: https://www.dane.gov.co/files/investigaciones/poblacion/cifras-definitivas-2019.pdf.

`python preparar_datos.py` reconstruye `mortalidad_2019.csv.gz`. El cruce territorial utiliza COD_DANE y el cruce de causas utiliza COD_MUERTE. Ambos se validan como muchos a uno: no multiplican ni eliminan defunciones. Se priorizan las descripciones de códigos completos y se incorporan también los códigos válidos de tres caracteres. Todas las causas presentes encuentran descripción en el catálogo.

Los controles de filas, correspondencia territorial y cobertura de causas se guardan en `validacion_fuentes.json`. Las huellas SHA-256 de los insumos y del consolidado están en `manifiesto.json`. Pandas lee la base comprimida directamente.

Cada fila representa una defunción y TOTAL vale uno. La geografía corresponde al lugar de ocurrencia registrado; no debe confundirse con residencia. Hay 1.110 códigos territoriales con registros, incluidas áreas no municipalizadas, en los 32 departamentos y Bogotá D. C. No se eliminan coincidencias de variables sin un identificador único de certificado.

No se dispone de población para estimar tasas. Los menores conteos corresponden únicamente a unidades con registros positivos: trece unidades tienen una defunción y se muestran diez mediante desempate por nombre, departamento y código. Los intervalos de GRUPO_EDAD1 son códigos de clasificación y no edades en años.

## Cartografía

`colombia.geo.json` contiene 33 geometrías departamentales. Fuente: https://gist.github.com/john-guerra/43c7656821069d00dcbc. Se añadió `properties.COD_DPTO` a partir de `properties.DPTO`, sin alterar las geometrías. Es un recurso de visualización y no certifica límites oficiales actualizados.

`../assets/world_110m.json` procede de https://cdn.plot.ly/world_110m.json y permite representar el mapa sin solicitudes cartográficas externas.
