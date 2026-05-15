# -*- coding: utf-8 -*-

from qgis.core import (QgsProcessing,
                       QgsProcessingAlgorithm,
                       QgsProcessingParameterFeatureSource,
                       QgsProcessingParameterRasterLayer,
                       QgsProcessingParameterBoolean,
                       QgsProcessingParameterFeatureSink,
                       QgsFeatureSink,
                       QgsFeature,
                       QgsField,
                       QgsFields,
                       QgsWkbTypes,
                       QgsGeometry,
                       QgsRectangle,
                       QgsCoordinateReferenceSystem,
                       QgsCoordinateTransform)
from qgis.PyQt.QtCore import QVariant
from osgeo import gdal, osr, ogr
import numpy as np
from .translations import tr

class ZonalStatsAlgorithm(QgsProcessingAlgorithm):
    # Constants for parameters
    INPUT_RASTER = 'INPUT_RASTER'
    INPUT_VECTOR = 'INPUT_VECTOR'
    OUTPUT = 'OUTPUT'
    
    # Stats Booleans
    STATS_MEAN = 'STATS_MEAN'
    STATS_SUM = 'STATS_SUM'
    STATS_MIN = 'STATS_MIN'
    STATS_MAX = 'STATS_MAX'
    STATS_STD = 'STATS_STD'
    STATS_VAR = 'STATS_VAR'
    STATS_COUNT = 'STATS_COUNT'
    STATS_COVERAGE = 'STATS_COVERAGE'
    STATS_VOLUME_INDEX = 'STATS_VOLUME_INDEX'
    STATS_VOLUME_M3 = 'STATS_VOLUME_M3'
    STATS_PABP25 = 'STATS_PABP25'
    STATS_PABP50 = 'STATS_PABP50'
    STATS_PABP75 = 'STATS_PABP75'
    
    # Percentiles Booleans
    P_VALS = [1, 5, 10, 15, 20, 25, 30, 35, 40, 45, 50, 55, 60, 65, 70, 75, 80, 85, 90, 95, 99]

    def initAlgorithm(self, config=None):
        self.addParameter(QgsProcessingParameterRasterLayer(self.INPUT_RASTER, tr('INPUT_RASTER')))
        self.addParameter(QgsProcessingParameterFeatureSource(self.INPUT_VECTOR, tr('INPUT_VECTOR'), [QgsProcessing.TypeVectorPolygon]))
        
        # Standard Stats
        self.addParameter(QgsProcessingParameterBoolean(self.STATS_MEAN, tr('STATS_MEAN'), False))
        self.addParameter(QgsProcessingParameterBoolean(self.STATS_SUM, tr('STATS_SUM'), False))
        self.addParameter(QgsProcessingParameterBoolean(self.STATS_MIN, tr('STATS_MIN'), False))
        self.addParameter(QgsProcessingParameterBoolean(self.STATS_MAX, tr('STATS_MAX'), False))
        self.addParameter(QgsProcessingParameterBoolean(self.STATS_STD, tr('STATS_STD'), False))
        self.addParameter(QgsProcessingParameterBoolean(self.STATS_VAR, tr('STATS_VAR'), False))
        self.addParameter(QgsProcessingParameterBoolean(self.STATS_COUNT, tr('STATS_COUNT'), False))
        self.addParameter(QgsProcessingParameterBoolean(self.STATS_COVERAGE, tr('STATS_COVERAGE'), False))
        self.addParameter(QgsProcessingParameterBoolean(self.STATS_VOLUME_INDEX, tr('STATS_VOLUME_INDEX'), False))
        self.addParameter(QgsProcessingParameterBoolean(self.STATS_VOLUME_M3, tr('STATS_VOLUME_M3'), False))
        self.addParameter(QgsProcessingParameterBoolean(self.STATS_PABP25, tr('STATS_PABP25'), False))
        self.addParameter(QgsProcessingParameterBoolean(self.STATS_PABP50, tr('STATS_PABP50'), False))
        self.addParameter(QgsProcessingParameterBoolean(self.STATS_PABP75, tr('STATS_PABP75'), False))
        
        # Percentiles
        for p in self.P_VALS:
            self.addParameter(QgsProcessingParameterBoolean(f'P{p}', f"{tr('PERCENTILE')} {p}", False))
            
        self.addParameter(QgsProcessingParameterFeatureSink(self.OUTPUT, tr('OUTPUT')))

    def processAlgorithm(self, parameters, context, feedback):
        raster_layer = self.parameterAsRasterLayer(parameters, self.INPUT_RASTER, context)
        vector_source = self.parameterAsSource(parameters, self.INPUT_VECTOR, context)
        
        if raster_layer is None or vector_source is None:
            raise QgsProcessingException(tr('INVALID_INPUTS'))

        # Check CRS compatibility
        if raster_layer.crs() != vector_source.sourceCrs():
            feedback.pushInfo(tr('REPROJECTING'))
            ct = QgsCoordinateTransform(vector_source.sourceCrs(), raster_layer.crs(), context.project())
        else:
            ct = None

        # Prepare stats to calculate
        stats_to_calc = []
        if self.parameterAsBool(parameters, self.STATS_MEAN, context): stats_to_calc.append('mean')
        if self.parameterAsBool(parameters, self.STATS_SUM, context): stats_to_calc.append('sum')
        if self.parameterAsBool(parameters, self.STATS_MIN, context): stats_to_calc.append('min')
        if self.parameterAsBool(parameters, self.STATS_MAX, context): stats_to_calc.append('max')
        if self.parameterAsBool(parameters, self.STATS_STD, context): stats_to_calc.append('std')
        if self.parameterAsBool(parameters, self.STATS_VAR, context): stats_to_calc.append('var')
        if self.parameterAsBool(parameters, self.STATS_COUNT, context): stats_to_calc.append('count')
        if self.parameterAsBool(parameters, self.STATS_COVERAGE, context): stats_to_calc.append('coverage')
        if self.parameterAsBool(parameters, self.STATS_VOLUME_INDEX, context): stats_to_calc.append('volume_index')
        if self.parameterAsBool(parameters, self.STATS_VOLUME_M3, context): stats_to_calc.append('volume_m3')
        if self.parameterAsBool(parameters, self.STATS_PABP25, context): stats_to_calc.append('pabp25')
        if self.parameterAsBool(parameters, self.STATS_PABP50, context): stats_to_calc.append('pabp50')
        if self.parameterAsBool(parameters, self.STATS_PABP75, context): stats_to_calc.append('pabp75')
        
        percentiles_to_calc = []
        for p in self.P_VALS:
            if self.parameterAsBool(parameters, f'P{p}', context):
                percentiles_to_calc.append(p)

        if not stats_to_calc and not percentiles_to_calc:
            raise QgsProcessingException(tr('SELECT_ONE'))

        # Prepare Output Fields
        fields = QgsFields(vector_source.fields())
        band_count = raster_layer.bandCount()
        
        # Add new fields - ORDER: Stat -> Bands
        # First standard stats
        for stat in stats_to_calc:
            if stat in ['coverage', 'volume_index', 'volume_m3', 'pabp25', 'pabp50', 'pabp75']: continue
            for b in range(1, band_count + 1):
                fields.append(QgsField(f"B{b}_{stat}", QVariant.Double))
        
        # Then percentiles
        for p in percentiles_to_calc:
            for b in range(1, band_count + 1):
                fields.append(QgsField(f"B{b}_p{p}", QVariant.Double))
                
        # Coverage (Single Field)
        if 'coverage' in stats_to_calc:
            fields.append(QgsField("Coverage_%", QVariant.Double))
        if 'volume_index' in stats_to_calc:
            fields.append(QgsField("Volume_Index", QVariant.Double))
        if 'volume_m3' in stats_to_calc:
            fields.append(QgsField("Volume_m3", QVariant.Double))
        if 'pabp25' in stats_to_calc:
            fields.append(QgsField("PABP_25", QVariant.Double))
        if 'pabp50' in stats_to_calc:
            fields.append(QgsField("PABP_50", QVariant.Double))
        if 'pabp75' in stats_to_calc:
            fields.append(QgsField("PABP_75", QVariant.Double))

        (sink, dest_id) = self.parameterAsSink(parameters, self.OUTPUT, context, fields, vector_source.wkbType(), raster_layer.crs())

        # Raster Data Access
        provider = raster_layer.dataProvider()
        x_res = raster_layer.rasterUnitsPerPixelX()
        y_res = raster_layer.rasterUnitsPerPixelY()
        extent = raster_layer.extent()
        width = raster_layer.width()
        height = raster_layer.height()
        
        feature_count = vector_source.featureCount()
        total = 100.0 / feature_count if feature_count > 0 else 0
        
        iterator = vector_source.getFeatures()
        for i, feature in enumerate(iterator):
            if feedback.isCanceled():
                break
            
            geom = feature.geometry()
            if ct:
                geom.transform(ct)
                
            bbox = geom.boundingBox()
            
            # Intersect bbox with raster extent
            intersect_bbox = bbox.intersect(extent)
            
            if intersect_bbox.isEmpty():
                # Feature outside raster
                new_feat = QgsFeature(feature)
                new_feat.setFields(fields, True) # init with existing attributes
                # Add nulls for new fields
                extra_attrs = [None] * (len(fields) - len(feature.attributes()))
                new_feat.setAttributes(feature.attributes() + extra_attrs)
                sink.addFeature(new_feat, QgsFeatureSink.FastInsert)
                feedback.setProgress(int(i * total))
                continue

            # Calculate pixel window
            col_start = int((intersect_bbox.xMinimum() - extent.xMinimum()) / x_res)
            row_start = int((extent.yMaximum() - intersect_bbox.yMaximum()) / y_res)
            col_end = int((intersect_bbox.xMaximum() - extent.xMinimum()) / x_res) + 1
            row_end = int((extent.yMaximum() - intersect_bbox.yMinimum()) / y_res) + 1
            
            # Clamp to raster dimensions
            col_start = max(0, col_start)
            row_start = max(0, row_start)
            col_end = min(width, col_end)
            row_end = min(height, row_end)
            
            win_width = col_end - col_start
            win_height = row_end - row_start
            
            if win_width <= 0 or win_height <= 0:
                 # Should not happen if bbox intersects, but safety check
                new_feat = QgsFeature(feature)
                new_feat.setFields(fields, True)
                extra_attrs = [None] * (len(fields) - len(feature.attributes()))
                new_feat.setAttributes(feature.attributes() + extra_attrs)
                sink.addFeature(new_feat, QgsFeatureSink.FastInsert)
                continue

            # Read Raster Block
            # Create a memory raster for the mask
            driver = gdal.GetDriverByName('MEM')
            mask_ds = driver.Create('', win_width, win_height, 1, gdal.GDT_Byte)
            mask_ds.SetGeoTransform((intersect_bbox.xMinimum(), x_res, 0, intersect_bbox.yMaximum(), 0, -y_res))
            
            # Use raster CRS WKT
            mask_ds.SetProjection(raster_layer.crs().toWkt())
            
            # Rasterize geometry
            ogr_ds = ogr.GetDriverByName('Memory').CreateDataSource('wrk')
            ogr_lyr = ogr_ds.CreateLayer('poly')
            ogr_feat = ogr.Feature(ogr_lyr.GetLayerDefn())
            ogr_geom = ogr.CreateGeometryFromWkt(geom.asWkt())
            ogr_feat.SetGeometry(ogr_geom)
            ogr_lyr.CreateFeature(ogr_feat)
            
            gdal.RasterizeLayer(mask_ds, [1], ogr_lyr, burn_values=[1])
            mask_array = mask_ds.ReadAsArray()
            
            # Clean up GDAL objects
            ogr_feat = None
            ogr_lyr = None
            ogr_ds = None
            mask_ds = None
            
            # Store results per band to reorder later
            # band_results = { band_index: { 'mean': val, 'p50': val ... } }
            band_results = {}
            coverage_val = None
            volume_index_val = None
            volume_m3_val = None
            pabp_vals = {'pabp25': None, 'pabp50': None, 'pabp75': None}
            
            # Try to open source with GDAL for efficiency
            source_path = raster_layer.source()
            use_gdal_direct = False
            ds = None
            try:
                # Only try GDAL direct if it's a file path
                if '://' not in source_path: 
                    ds = gdal.Open(source_path)
                    if ds: use_gdal_direct = True
            except:
                pass
            
            for b in range(1, band_count + 1):
                band_results[b] = {}
                data_array = None
                no_data_val = provider.sourceNoDataValue(b)

                if use_gdal_direct:
                    band = ds.GetRasterBand(b)
                    data_array = band.ReadAsArray(col_start, row_start, win_width, win_height)
                    if data_array is None:
                         # Fallback to QGIS provider if GDAL fails on window
                         pass
                    else:
                        no_data_val = band.GetNoDataValue()
                
                if data_array is None:
                    # Fallback to QGIS API
                    block = provider.block(b, intersect_bbox, win_width, win_height)
                    if block:
                        # This is tricky because block.data() is bytes. 
                        # For now, let's rely on GDAL direct or fail gracefully for this prototype.
                        # Implementing block-to-numpy manually is verbose.
                        # Let's assume most users use file-based rasters.
                        pass

                if data_array is None:
                    continue

                # Masking
                valid_pixels = data_array[mask_array == 1]
                
                # Filter NoData
                if no_data_val is not None:
                    if np.isnan(no_data_val):
                        valid_pixels = valid_pixels[~np.isnan(valid_pixels)]
                    else:
                        valid_pixels = valid_pixels[valid_pixels != no_data_val]
                
                if valid_pixels.size == 0:
                    continue
                
                # Calculate Stats
                if 'mean' in stats_to_calc: band_results[b]['mean'] = float(np.mean(valid_pixels))
                if 'sum' in stats_to_calc: band_results[b]['sum'] = float(np.sum(valid_pixels))
                if 'min' in stats_to_calc: band_results[b]['min'] = float(np.min(valid_pixels))
                if 'max' in stats_to_calc: band_results[b]['max'] = float(np.max(valid_pixels))
                if 'std' in stats_to_calc: band_results[b]['std'] = float(np.std(valid_pixels))
                if 'var' in stats_to_calc: band_results[b]['var'] = float(np.var(valid_pixels))
                if 'count' in stats_to_calc: band_results[b]['count'] = int(valid_pixels.size)
                
                # Calculate Coverage (Only once, using Band 1 as reference)
                if 'coverage' in stats_to_calc and b == 1:
                    total_poly_pixels = np.sum(mask_array == 1)
                    if total_poly_pixels > 0:
                        cov = (valid_pixels.size / total_poly_pixels) * 100.0
                    else:
                        cov = 0.0
                    coverage_val = float(cov)
                
                # Calculate Volume Index (Only once, using Band 1 as reference - assumes single band DEM or Band 1 is height)
                if 'volume_index' in stats_to_calc and b == 1:
                    # Formula: (Sum(Heights > 0) * GSD) / ROI_Area
                    # Filter heights > 0 (soil noise filtering)
                    heights = valid_pixels[valid_pixels > 0]
                    sum_heights = np.sum(heights)
                    
                    # GSD (Linear) - using x_res (assuming square pixels mostly, or user wants linear dimension)
                    gsd_linear = x_res 
                    
                    # ROI Area
                    roi_area = geom.area()
                    
                    if roi_area > 0:
                        vol_idx = (sum_heights * gsd_linear) / roi_area
                    else:
                        vol_idx = 0.0
                    
                    volume_index_val = float(vol_idx)

                # Calculate Pure Volume (m3) (Only once, using Band 1 as reference)
                if 'volume_m3' in stats_to_calc and b == 1:
                    # Formula: Sum(Heights > 0) * (pixel_area)
                    # Filter heights > 0
                    heights = valid_pixels[valid_pixels > 0]
                    sum_heights = np.sum(heights)
                    
                    # Pixel Area = x_res * y_res
                    pixel_area = x_res * y_res
                    
                    vol_m3 = sum_heights * pixel_area
                    volume_m3_val = float(vol_m3)
                
                # Calculate PABP (Only once, using Band 1 as reference)
                # PABP = Count(h < Px) / Total_Pixels_ROI (Using ALL pixels, NO filter > 0)
                pabp_requested = [k for k in ['pabp25', 'pabp50', 'pabp75'] if k in stats_to_calc]
                if pabp_requested and b == 1:
                    # Use ALL valid pixels (including soil/zeros)
                    all_pixels = valid_pixels
                    
                    if all_pixels.size > 0:
                        # Calculate percentiles of ALL pixels
                        p_targets = []
                        if 'pabp25' in stats_to_calc: p_targets.append(25)
                        if 'pabp50' in stats_to_calc: p_targets.append(50)
                        if 'pabp75' in stats_to_calc: p_targets.append(75)
                        
                        p_values = np.percentile(all_pixels, p_targets)
                        p_map = dict(zip(p_targets, p_values))
                        
                        total_pixels = all_pixels.size
                        
                        if 'pabp25' in stats_to_calc:
                            count = np.sum(all_pixels < p_map[25])
                            pabp_vals['pabp25'] = float(count / total_pixels)
                        if 'pabp50' in stats_to_calc:
                            count = np.sum(all_pixels < p_map[50])
                            pabp_vals['pabp50'] = float(count / total_pixels)
                        if 'pabp75' in stats_to_calc:
                            count = np.sum(all_pixels < p_map[75])
                            pabp_vals['pabp75'] = float(count / total_pixels)
                    else:
                        for k in pabp_requested: pabp_vals[k] = 0.0

                # Calculate Percentiles
                if percentiles_to_calc:
                    p_res = np.percentile(valid_pixels, percentiles_to_calc)
                    for idx, p in enumerate(percentiles_to_calc):
                        band_results[b][p] = float(p_res[idx])

            # Flatten results into attributes in correct order
            new_attributes = []
            
            # Order: Stat -> Bands
            for stat in stats_to_calc:
                if stat in ['coverage', 'volume_index', 'volume_m3', 'pabp25', 'pabp50', 'pabp75']: continue
                for b in range(1, band_count + 1):
                    val = band_results.get(b, {}).get(stat, None)
                    new_attributes.append(val)
            
            for p in percentiles_to_calc:
                for b in range(1, band_count + 1):
                    val = band_results.get(b, {}).get(p, None)
                    new_attributes.append(val)
                    
            if 'coverage' in stats_to_calc:
                new_attributes.append(coverage_val)
            if 'volume_index' in stats_to_calc:
                new_attributes.append(volume_index_val)
            if 'volume_m3' in stats_to_calc:
                new_attributes.append(volume_m3_val)
            if 'pabp25' in stats_to_calc:
                new_attributes.append(pabp_vals['pabp25'])
            if 'pabp50' in stats_to_calc:
                new_attributes.append(pabp_vals['pabp50'])
            if 'pabp75' in stats_to_calc:
                new_attributes.append(pabp_vals['pabp75'])

            # Add feature to sink
            new_feat = QgsFeature(feature)
            new_feat.setFields(fields, True)
            new_feat.setAttributes(feature.attributes() + new_attributes)
            sink.addFeature(new_feat, QgsFeatureSink.FastInsert)
            
            feedback.setProgress(int(i * total))

        return {self.OUTPUT: dest_id}

    def name(self):
        return 'magic_stats_extractor'

    def displayName(self):
        return tr('NAME')

    def group(self):
        return tr('GROUP')

    def groupId(self):
        return 'rasteranalysis'

    def createInstance(self):
        return ZonalStatsAlgorithm()

    def shortHelpString(self):
        return tr('HELP_DESC')
