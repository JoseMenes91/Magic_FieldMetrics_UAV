import numpy as np
from osgeo import gdal, ogr, osr
import os

def create_verification_data(output_dir):
    # 1. Define Paths
    raster_path = os.path.join(output_dir, 'verify_raster.tif')
    vector_path = os.path.join(output_dir, 'verify_vector.shp')

    # 2. Create Raster (10x10, 1m resolution, Value=10.0)
    driver = gdal.GetDriverByName('GTiff')
    ds = driver.Create(raster_path, 10, 10, 1, gdal.GDT_Float32)
    
    # GeoTransform: TopLeftX, PixelWidth, 0, TopLeftY, 0, PixelHeight
    # Origin at (0, 10), 1m pixels. Y goes down (-1).
    ds.SetGeoTransform([0, 1, 0, 10, 0, -1])
    
    # CRS: WGS84 UTM Zone 33N (EPSG:32633) - Just a metric CRS
    srs = osr.SpatialReference()
    srs.ImportFromEPSG(32633)
    ds.SetProjection(srs.ExportToWkt())
    
    # Write Data: Constant value 10.0
    band = ds.GetRasterBand(1)
    data = np.full((10, 10), 10.0, dtype=np.float32)
    
    band.WriteArray(data)
    band.SetNoDataValue(-9999)
    ds.FlushCache()
    ds = None # Close

    # 3. Create Vector (Square 6x6, aligned to pixels)
    driver = ogr.GetDriverByName('ESRI Shapefile')
    if os.path.exists(vector_path):
        driver.DeleteDataSource(vector_path)
    ds = driver.CreateDataSource(vector_path)
    layer = ds.CreateLayer('verify_poly', srs, ogr.wkbPolygon)
    
    # Add an ID field
    layer.CreateField(ogr.FieldDefn('id', ogr.OFTInteger))
    
    # Create Feature
    feature = ogr.Feature(layer.GetLayerDefn())
    feature.SetField('id', 1)
    
    wkt = "POLYGON ((2 2, 2 8, 8 8, 8 2, 2 2))"
    geom = ogr.CreateGeometryFromWkt(wkt)
    feature.SetGeometry(geom)
    
    layer.CreateFeature(feature)
    ds = None # Close

    print(f"Data generated successfully:")
    print(f"Raster: {raster_path}")
    print(f"Vector: {vector_path}")
    print("-" * 30)
    print("EXPECTED RESULTS (Metric CRS):")
    print("Polygon Area: 36 m2")
    print("Pixel Size: 1x1 m")
    print("Pixel Value: 10.0")
    print("Count: 36")
    print("Sum: 360.0")
    print("Mean: 10.0")
    print("Volume m3: 360.0")
    print("Volume Index: 10.0")

if __name__ == "__main__":
    create_verification_data(os.getcwd())
