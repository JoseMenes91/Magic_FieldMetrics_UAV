# Magic FieldMetrics - UAV (QGIS Plugin)

Un plugin avanzado para QGIS diseñado para el fenotipado de alto rendimiento y análisis de ensayos agrícolas a partir de vuelos UAV (VANT).

## Características Principales
- **Estadísticas Clásicas:** Media, Suma, Mínimo, Máximo, Desvío Estándar, Varianza, Conteo y Percentiles personalizables (P1-P99).
- **Cobertura Vegetal (%):** Calcula la proporción de vegetación real (requiere ortomosaico con suelo enmascarado).
- **Métricas de Volumen (Altimetría):** 
  - *Volumen de Canopeo ($m^3$)*: Integración espacial de la altura de la planta.
  - *Índice de Volumen*: Normalización del volumen por el área de la parcela.
- **Uniformidad Intrapoblacional:** Coeficiente de Variación (CV).
- **Métricas de Contexto Global (Ensayo Completo):**
  - *Z-Score*: Estandariza la parcela frente a la Media y Desviación Estándar de todo el ensayo.
  - *Escalamiento Robusto (Robust Scaler)*: Estadarización resistente a valores atípicos (malezas) usando Mediana y Rango Intercuartílico global.
- Soporta procesamiento multibanda.
- Desarrollado usando `GDAL` y `NumPy` para máxima velocidad.

## Instalación

1. Clona o descarga este repositorio.
2. Copia la carpeta `magic_stats_extractor` dentro de tu directorio de plugins de QGIS (usualmente en `%APPDATA%\QGIS\QGIS3\profiles\default\python\plugins` en Windows).
3. Reinicia QGIS y activa el plugin "Magic FieldMetrics - UAV" desde el administrador de complementos.

## Uso

1. Abre la **Caja de Herramientas de Procesos** (`Ctrl+Alt+T`).
2. Ve a **Análisis Raster** -> **Magic FieldMetrics - UAV**.
3. Selecciona tu raster de entrada (Ortomosaico o MDS) y tu capa vectorial de parcelas.
4. Selecciona las métricas que deseas exportar.
5. Haz clic en Ejecutar para obtener una nueva capa vectorial con las estadísticas integradas en la tabla de atributos.
