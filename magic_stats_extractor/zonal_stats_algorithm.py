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
                       QgsCoordinateTransform,
                       QgsDistanceArea,
                       QgsUnitTypes,
                       QgsPointXY,
                       QgsRaster)
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
    STATS_CV = 'STATS_CV'
    STATS_ZSCORE = 'STATS_ZSCORE'
    STATS_ROBUST_SCALER = 'STATS_ROBUST_SCALER'
    
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
        self.addParameter(QgsProcessingParameterBoolean(self.STATS_CV, tr('STATS_CV'), False))
        self.addParameter(QgsProcessingParameterBoolean(self.STATS_ZSCORE, tr('STATS_ZSCORE'), False))
        self.addParameter(QgsProcessingParameterBoolean(self.STATS_ROBUST_SCALER, tr('STATS_ROBUST_SCALER'), False))
        
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
        if self.parameterAsBool(parameters, self.STATS_CV, context): stats_to_calc.append('cv')
        if self.parameterAsBool(parameters, self.STATS_ZSCORE, context): stats_to_calc.append('zscore')
        if self.parameterAsBool(parameters, self.STATS_ROBUST_SCALER, context): stats_to_calc.append('robust_scaler')
        
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
            if stat in ['coverage', 'volume_index', 'volume_m3', 'zscore', 'robust_scaler']: continue
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
        if 'zscore' in stats_to_calc:
            for b in range(1, band_count + 1):
                fields.append(QgsField(f"B{b}_Z_Score", QVariant.Double))
        if 'robust_scaler' in stats_to_calc:
            for b in range(1, band_count + 1):
                fields.append(QgsField(f"B{b}_RobScal", QVariant.Double))

        (sink, dest_id) = self.parameterAsSink(parameters, self.OUTPUT, context, fields, vector_source.wkbType(), raster_layer.crs())

        # Raster Data Access
        provider = raster_layer.dataProvider()
        x_res = raster_layer.rasterUnitsPerPixelX()
        y_res = raster_layer.rasterUnitsPerPixelY()
        extent = raster_layer.extent()
        width = raster_layer.width()
        height = raster_layer.height()
        
        # CRS Check & Metric Conversion Setup
        source_crs = raster_layer.crs()
        is_geographic = source_crs.isGeographic()
        
        da = QgsDistanceArea()
        da.setSourceCrs(source_crs, context.transformContext())
        
        # Calculate Metric Factor for GSD if Geographic
        metric_factor_sq = 1.0
        metric_factor_linear = 1.0
        
        if is_geographic:
            feedback.pushInfo(tr('Geographic CRS detected. Converting to meters...'))
            da.setEllipsoid(context.project().ellipsoid())
            # Measure 1 degree in meters at the center latitude
            center = extent.center()
            # Approx conversion: measure distance of 1 pixel width in meters
            p1 = center
            p2 = QgsPointXY(center.x() + x_res, center.y())
            pixel_width_m = da.measureLine(p1, p2)
            
            p3 = QgsPointXY(center.x(), center.y() - y_res)
            pixel_height_m = da.measureLine(p1, p3)
            
            metric_factor_linear = pixel_width_m / x_res # meters per degree (approx)
            
            # Update GSD to meters for calculations
            gsd_m2 = pixel_width_m * pixel_height_m
            gsd_linear_m = pixel_width_m
            feedback.pushInfo(f"Estimated GSD: {gsd_linear_m:.4f} m, Area: {gsd_m2:.6f} m2")
        else:
            # Projected - assume meters (or user units)
            gsd_m2 = x_res * y_res
            gsd_linear_m = x_res

        # GLOBAL Z-SCORE & ROBUST SCALER PRE-CALCULATION
        global_p_map = {} # {band: {25: val, 50: val...}}
        global_stats = {} # {band: {'mean': val, 'std': val}}
        
        zscore_requested = 'zscore' in stats_to_calc
        robust_scaler_requested = 'robust_scaler' in stats_to_calc
        
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

        if zscore_requested or robust_scaler_requested:
            feedback.pushInfo("Scanning Global Statistics...")
            # Store valid pixels per band: { band_idx: [array1, array2...] }
            all_valid_pixels = {b: [] for b in range(1, band_count + 1)}
            # feedback.pushInfo(f"Initialized global scan for {band_count} bands.")
            
            iterator_scan = vector_source.getFeatures()
            total_feats = vector_source.featureCount()
            step = max(1, int(total_feats / 10))
            
            # Use QGIS Provider for NoData value
            no_data_vals = {b: provider.sourceNoDataValue(b) for b in range(1, band_count + 1)}

            # Use QGIS Provider for NoData value
            no_data_vals = {b: provider.sourceNoDataValue(b) for b in range(1, band_count + 1)}
            
            for i, feature in enumerate(iterator_scan):
                if feedback.isCanceled(): break
                
                geom = feature.geometry()
                if ct: geom.transform(ct)
                bbox = geom.boundingBox()
                intersect_bbox = bbox.intersect(extent)
                
                if intersect_bbox.isEmpty(): continue
                
                col_start = int((intersect_bbox.xMinimum() - extent.xMinimum()) / x_res)
                row_start = int((extent.yMaximum() - intersect_bbox.yMaximum()) / y_res)
                col_end = int((intersect_bbox.xMaximum() - extent.xMinimum()) / x_res) + 1
                row_end = int((extent.yMaximum() - intersect_bbox.yMinimum()) / y_res) + 1
                
                col_start = max(0, col_start)
                row_start = max(0, row_start)
                col_end = min(width, col_end)
                row_end = min(height, row_end)
                
                win_width = col_end - col_start
                win_height = row_end - row_start
                
                if win_width <= 0 or win_height <= 0: continue
                
                # Mask
                driver = gdal.GetDriverByName('MEM')
                mask_ds = driver.Create('', win_width, win_height, 1, gdal.GDT_Byte)
                mask_ds.SetGeoTransform((intersect_bbox.xMinimum(), x_res, 0, intersect_bbox.yMaximum(), 0, -y_res))
                mask_ds.SetProjection(raster_layer.crs().toWkt())
                
                ogr_ds = ogr.GetDriverByName('Memory').CreateDataSource('wrk')
                ogr_lyr = ogr_ds.CreateLayer('poly')
                ogr_feat = ogr.Feature(ogr_lyr.GetLayerDefn())
                ogr_geom = ogr.CreateGeometryFromWkt(geom.asWkt())
                ogr_feat.SetGeometry(ogr_geom)
                ogr_lyr.CreateFeature(ogr_feat)
                
                gdal.RasterizeLayer(mask_ds, [1], ogr_lyr, burn_values=[1])
                mask_array = mask_ds.ReadAsArray()
                
                # Read Bands using QGIS Data Provider
                # We need to scan ALL bands if ZScore/RobustScaler are requested
                
                for b in range(1, band_count + 1):
                    try:
                        data_array = None
                        
                        # Method 1: GDAL Direct (Fastest)
                        if use_gdal_direct:
                            try:
                                band = ds.GetRasterBand(b)
                                # GDAL ReadAsArray returns numpy array directly
                                data_array = band.ReadAsArray(col_start, row_start, win_width, win_height)
                            except Exception as e_gdal:
                                # feedback.pushInfo(f"GDAL Read failed B{b}: {e_gdal}")
                                data_array = None
                        
                        # Method 2: QGIS Block (Fast but tricky with padding)
                        if data_array is None:
                            block = provider.block(b, intersect_bbox, win_width, win_height)
                            if block and block.isValid():
                                data_bytes = block.data()
                                dt = provider.dataType(b)
                                np_dtype = np.float32
                                
                                # QGIS Raster Data Types
                                if dt == 0: np_dtype = np.uint8
                                elif dt == 1: np_dtype = np.uint16
                                elif dt == 2: np_dtype = np.int16
                                elif dt == 3: np_dtype = np.uint32
                                elif dt == 4: np_dtype = np.int32
                                elif dt == 5: np_dtype = np.float32
                                elif dt == 6: np_dtype = np.float64
                                
                                try:
                                    raw_array = np.frombuffer(data_bytes, dtype=np_dtype)
                                    data_array = raw_array.reshape((win_height, win_width))
                                except:
                                    # Fallback: Pixel by pixel (Slow but safe)
                                    valid_pixels_list = []
                                    for r in range(win_height):
                                        for c in range(win_width):
                                            if mask_array[r, c] == 1:
                                                val = block.value(r, c)
                                                if not block.isNoData(r, c):
                                                    valid_pixels_list.append(val)
                                    if valid_pixels_list:
                                        # Create array directly from list
                                        # Skip the standard processing below since we already filtered
                                        all_valid_pixels[b].append(np.array(valid_pixels_list))
                                        continue 

                        # Process data_array (from GDAL or QGIS Block success)
                        if data_array is not None:
                            if data_array.shape != mask_array.shape:
                                # feedback.pushInfo(f"Shape mismatch B{b}: Data {data_array.shape} vs Mask {mask_array.shape}")
                                pass
                            
                            if data_array.shape == mask_array.shape:
                                valid_pixels = data_array[mask_array == 1]
                            
                            nd_val = no_data_vals[b]
                            if nd_val is not None and not np.isnan(nd_val):
                                    valid_pixels = valid_pixels[valid_pixels != nd_val]
                            
                            if np.issubdtype(data_array.dtype, np.floating):
                                valid_pixels = valid_pixels[~np.isnan(valid_pixels)]

                            if valid_pixels.size > 0:
                                all_valid_pixels[b].append(valid_pixels)
                                
                    except Exception as e:
                        # feedback.pushInfo(f"Error reading band {b} feat {i}: {e}")
                        pass
                
                if i % step == 0:
                    feedback.setProgress(int((i / total_feats) * 10))
            
            # Process accumulated pixels for each band
            for b in range(1, band_count + 1):
                pixels_list = all_valid_pixels[b]
                if not pixels_list:
                    continue
                    
                # feedback.pushInfo(f"Concatenating global pixels for Band {b}...")
                global_pixels = np.concatenate(pixels_list)
                # feedback.pushInfo(f"Band {b}: Total pixels for global stats: {global_pixels.size}")
                
                # Initialize band storage
                global_p_map[b] = {}
                global_stats[b] = {'mean': None, 'std': None}

                # 1. Percentiles (for Robust Scaler)
                if robust_scaler_requested:
                    p_targets = []
                    needed_ps = set()
                    
                    if robust_scaler_requested:
                        needed_ps.add(25)
                        needed_ps.add(50)
                        needed_ps.add(75)
                    
                    if needed_ps:
                        p_targets = sorted(list(needed_ps))
                        p_values = np.percentile(global_pixels, p_targets)
                        # Store in map
                        for idx, p in enumerate(p_targets):
                            global_p_map[b][p] = p_values[idx]
                
                # 2. Z-Score Global Stats
                if zscore_requested:
                    # Standard Z-Score (No filtering)
                    global_stats[b]['mean'] = np.mean(global_pixels)
                    global_stats[b]['std'] = np.std(global_pixels)
                    
                    # feedback.pushInfo(f"Band {b} Global Stats: Mean={global_stats[b]['mean']}, Std={global_stats[b]['std']}")

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
            # ZScore and Robust Scaler are now per band, stored in band_results
            # band_results[b]['zscore'] = ...
            
            # Clean up per-feature GDAL objects
            # ds is now persistent, so we don't re-open it here
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
                    if block and block.isValid():
                        try:
                            # Try efficient buffer read
                            dt = provider.dataType(b)
                            np_dtype = np.float32
                            
                            # Correct QGIS DataType Mapping
                            if dt == 1: np_dtype = np.uint8
                            elif dt == 2: np_dtype = np.uint16
                            elif dt == 3: np_dtype = np.int16
                            elif dt == 4: np_dtype = np.uint32
                            elif dt == 5: np_dtype = np.int32
                            elif dt == 6: np_dtype = np.float32
                            elif dt == 7: np_dtype = np.float64
                            
                            data_bytes = block.data()
                            raw_array = np.frombuffer(data_bytes, dtype=np_dtype)
                            data_array = raw_array.reshape((win_height, win_width))
                        except:
                            # Fallback: Pixel by pixel reconstruction (Slow but robust)
                            try:
                                temp_data = np.zeros((win_height, win_width), dtype=np.float32)
                                for r in range(win_height):
                                    for c in range(win_width):
                                        val = block.value(r, c)
                                        temp_data[r, c] = val
                                data_array = temp_data
                            except:
                                data_array = None

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
                if 'cv' in stats_to_calc:
                    mean_val = float(np.mean(valid_pixels))
                    std_val = float(np.std(valid_pixels))
                    if mean_val != 0:
                        band_results[b]['cv'] = (std_val / mean_val) * 100.0
                    else:
                        band_results[b]['cv'] = 0.0
                
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
                    # If geographic, calculate ellipsoidal area in meters
                    if is_geographic:
                        roi_area = da.measureArea(geom)
                    else:
                        roi_area = geom.area()
                    
                    if roi_area > 0:
                        # Use gsd_linear_m (converted to meters if needed)
                        vol_idx = (sum_heights * gsd_linear_m) / roi_area
                    else:
                        vol_idx = 0.0
                    
                    volume_index_val = float(vol_idx)

                # Calculate Pure Volume (m3) (Only once, using Band 1 as reference)
                if 'volume_m3' in stats_to_calc and b == 1:
                    # Formula: Sum(Heights > 0) * (pixel_area_m2)
                    # Filter heights > 0
                    heights = valid_pixels[valid_pixels > 0]
                    sum_heights = np.sum(heights)
                    
                    # Use gsd_m2 (converted to meters squared if needed)
                    vol_m3 = sum_heights * gsd_m2
                    volume_m3_val = float(vol_m3)
                

                # Calculate Z-Score (For CURRENT Band)
                if zscore_requested:
                    g_stats = global_stats.get(b, {})
                    g_mean = g_stats.get('mean')
                    g_std = g_stats.get('std')
                    
                    z_val = None
                    if g_mean is not None and g_std is not None and g_std > 0:
                        # Use mean if already calc, else calc it
                        if 'mean' in band_results[b]:
                            plot_mean = band_results[b]['mean']
                        elif valid_pixels.size > 0:
                            plot_mean = np.mean(valid_pixels)
                        else:
                            plot_mean = None
                            
                        if plot_mean is not None:
                            z_val = float((plot_mean - g_mean) / g_std)
                    
                    band_results[b]['zscore'] = z_val

                # Calculate Robust Scaler (For CURRENT Band)
                if robust_scaler_requested:
                    g_map = global_p_map.get(b, {})
                    p25 = g_map.get(25)
                    p50 = g_map.get(50)
                    p75 = g_map.get(75)
                    
                    rs_val = None
                    if p25 is not None and p50 is not None and p75 is not None:
                        iqr = p75 - p25
                        if iqr > 0:
                            if 'mean' in band_results[b]:
                                plot_mean = band_results[b]['mean']
                            elif valid_pixels.size > 0:
                                plot_mean = np.mean(valid_pixels)
                            else:
                                plot_mean = None
                                
                            if plot_mean is not None:
                                rs_val = float((plot_mean - p50) / iqr)
                    
                    band_results[b]['robust_scaler'] = rs_val

                # Calculate Percentiles
                if percentiles_to_calc:
                    p_res = np.percentile(valid_pixels, percentiles_to_calc)
                    for idx, p in enumerate(percentiles_to_calc):
                        band_results[b][p] = float(p_res[idx])

            # Flatten results into attributes in correct order
            new_attributes = []
            
            # Order: Stat -> Bands
            for stat in stats_to_calc:
                if stat in ['coverage', 'volume_index', 'volume_m3', 'zscore', 'robust_scaler']: continue
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
            if 'zscore' in stats_to_calc:
                for b in range(1, band_count + 1):
                    new_attributes.append(band_results.get(b, {}).get('zscore', None))
            if 'robust_scaler' in stats_to_calc:
                for b in range(1, band_count + 1):
                    new_attributes.append(band_results.get(b, {}).get('robust_scaler', None))

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
