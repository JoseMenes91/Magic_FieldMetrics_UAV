# -*- coding: utf-8 -*-

from qgis.core import QgsSettings

class Translator:
    """Simple translation helper."""
    
    def __init__(self):
        self.locale = QgsSettings().value('locale/userLocale', 'en')[0:2]
        
        self.translations = {
            'es': {
                'INPUT_RASTER': 'Capa Raster (Mosaico)',
                'INPUT_VECTOR': 'Capa Vectorial (Grilla/Polígonos)',
                'STATS_MEAN': 'Media',
                'STATS_SUM': 'Suma',
                'STATS_MIN': 'Mínimo',
                'STATS_MAX': 'Máximo',
                'STATS_STD': 'Desvío Estándar',
                'STATS_VAR': 'Varianza',
                'STATS_COUNT': 'Conteo de Píxeles',
                'STATS_COVERAGE': 'Cobertura (%) (se necesita el raster con el suelo enmascarado)',
                'STATS_VOLUME_INDEX': 'Índice de Volumen (Solo para Modelos de Altura de Planta)',
                'STATS_VOLUME_M3': 'Volumen de Canopeo (m³) (Solo para Modelos de Altura de Planta)',
                'STATS_PABP25': 'PABP 25 (Proporción de Área Bajo Percentil 25)',
                'STATS_PABP50': 'PABP 50 (Proporción de Área Bajo Percentil 50)',
                'STATS_PABP75': 'PABP 75 (Proporción de Área Bajo Percentil 75)',
                'OUTPUT': 'Vector de Salida',
                'PERCENTILE': 'Percentil',
                'INVALID_INPUTS': 'Entradas inválidas',
                'REPROJECTING': 'Reproyectando vector al CRS del raster para el análisis...',
                'SELECT_ONE': 'Seleccione al menos una estadística o percentil.',
                'NAME': 'Magic FieldMetrics - UAV',
                'GROUP': 'Análisis Raster',
                'HELP_DESC': '**Magic FieldMetrics - UAV** está diseñado para extraer información de ortomosaicos en ensayos de campo.\n\n**Metodología**: La herramienta analiza cada parcela (polígono) de la capa vectorial, extrayendo los valores de los píxeles mediante la geometría exacta. A partir de estos datos, se extraen múltiples estadísticas de todas las bandas disponibles en la imagen raster.\n\n**Índice de Volumen**: El plugin realiza un proceso de integración espacial en dos pasos automáticos:\n1. **Integración**: Suma todas las alturas de los píxeles válidos (>0) y las multiplica por la resolución del sensor (GSD). (Requiere Modelo Digital de Elevación con altura de planta).\n2. Divide el resultado por el área total de la parcela.\n\nEl resultado es un índice adimensional.\n\n**Volumen de Canopeo (m³)**: Calcula el volumen físico total de la vegetación en la parcela. Fórmula: Suma(Alturas > 0) * (GSD^2). **NOTA**: Solo válido para Modelos Digitales de Elevación que representen altura de planta (suelo ~ 0).\n\n**PABP (Proporción de Área Bajo el Percentil)**: Fracción de la superficie de la parcela que se encuentra por debajo de un umbral de altura determinado (P25, P50, P75 calculados sobre TODA la parcela, incluido suelo). Fórmula: Conteo(h < Px) / Total_Píxeles_ROI. Adimensional (0-1). Requiere Modelo de Altura.\n\nAdemás, calcula la **Cobertura (%)** vegetal. La cobertura se define como la proporción de píxeles válidos (planta) respecto al total de píxeles dentro de la geometría de la parcela. Para ello, la imagen raster utilizada debe tener el suelo enmascarado.\n\n*Powered by GDAL & NumPy.*'
            },
            'en': {
                'INPUT_RASTER': 'Raster Layer (Mosaic)',
                'INPUT_VECTOR': 'Vector Layer (Grid/Polygons)',
                'STATS_MEAN': 'Mean',
                'STATS_SUM': 'Sum',
                'STATS_MIN': 'Minimum',
                'STATS_MAX': 'Maximum',
                'STATS_STD': 'Standard Deviation',
                'STATS_VAR': 'Variance',
                'STATS_COUNT': 'Pixel Count',
                'STATS_COVERAGE': 'Coverage (%) (requires raster with masked soil)',
                'STATS_VOLUME_INDEX': 'Volume Index (Plant Height Models Only)',
                'STATS_VOLUME_M3': 'Canopy Volume (m³) (Plant Height Models Only)',
                'STATS_PABP25': 'PABP 25 (Proportion of Area Below Percentile 25)',
                'STATS_PABP50': 'PABP 50 (Proportion of Area Below Percentile 50)',
                'STATS_PABP75': 'PABP 75 (Proportion of Area Below Percentile 75)',
                'OUTPUT': 'Output Vector',
                'PERCENTILE': 'Percentile',
                'INVALID_INPUTS': 'Invalid inputs',
                'REPROJECTING': 'Reprojecting vector to raster CRS for analysis...',
                'SELECT_ONE': 'Select at least one statistic or percentile.',
                'NAME': 'Magic FieldMetrics - UAV',
                'GROUP': 'Raster Analysis',
                'HELP_DESC': '**Magic FieldMetrics - UAV** is designed to extract information from orthomosaics in field trials.\n\n**Methodology**: The tool analyzes each plot (polygon) from the vector layer, extracting pixel values using the exact geometry. From this data, multiple statistics are extracted from all available bands in the raster image.\n\n**Volume Index**: The plugin performs a spatial integration process in two automatic steps:\n1. **Integration**: Sums all valid pixel heights (>0) and multiplies by sensor resolution (GSD). (Requires Digital Elevation Model with plant height).\n2. Divides the result by the total plot area.\n\nThe result is a dimensionless index.\n\n**Canopy Volume (m³)**: Calculates the total physical volume of vegetation in the plot. Formula: Sum(Heights > 0) * (GSD^2). **NOTE**: Only valid for Digital Elevation Models representing plant height (soil ~ 0).\n\n**PABP (Proportion of Area Below Percentile)**: Fraction of the plot area that is below a certain height threshold (P25, P50, P75 calculated over the ENTIRE plot, including soil). Formula: Count(h < Px) / Total_ROI_Pixels. Dimensionless (0-1). Requires Height Model.\n\nAdditionally, it calculates vegetal **Coverage (%)**. Coverage is defined as the proportion of valid pixels (plant) relative to the total pixels within the plot geometry. For this, the raster image used must have the soil masked.\n\n*Powered by GDAL & NumPy.*'
            }
        }

    def tr(self, key):
        """Get translated text."""
        # Default to English if not Spanish
        lang_code = 'es' if self.locale == 'es' else 'en'
        return self.translations.get(lang_code, {}).get(key, key)

# Global instance
_translator = Translator()

def tr(key):
    return _translator.tr(key)
