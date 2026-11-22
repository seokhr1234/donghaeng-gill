#!/usr/bin/env python3
"""Prepare a display-only 30 m surface-slope raster for all 25 Seoul districts."""

import argparse
import csv
from hashlib import sha256
import json
from pathlib import Path

import numpy as np
from osgeo import gdal, ogr, osr


HERE = Path(__file__).resolve().parent
BOUNDARY = HERE.parent / 'seoul-rest-2026-11-20/derived/osm-boundaries.geojson'
BOUNDARY_ID = 'relation/2297418'
GRID = 30
NODATA = -9999
TILES = {
    'Copernicus_DSM_COG_10_N37_00_E126_00_DEM': 'f530dd28308ecd6c5ceb0405dc1ffb7113bcafdec30d023de50f16dc433a274f',
    'Copernicus_DSM_COG_10_N37_00_E127_00_DEM': '4f8fef79da8c18ed9a9a0fb97b3d2695c4681181e013e039d87044e5479f7df6',
}
ATTRIBUTION = ('Produced using Copernicus WorldDEM-30 © DLR e.V. 2010-2014 and '
               '© Airbus Defence and Space GmbH 2014-2018 provided under COPERNICUS '
               'by the European Union and ESA; all rights reserved. Boundary © OpenStreetMap contributors.')


def rasterize(layer, grid, field=None):
    raster = gdal.GetDriverByName('MEM').Create('', grid.RasterXSize, grid.RasterYSize, 1, gdal.GDT_Byte)
    raster.SetProjection(grid.GetProjection())
    raster.SetGeoTransform(grid.GetGeoTransform())
    if field:
        gdal.RasterizeLayer(raster, [1], layer, options=[f'ATTRIBUTE={field}'])
    else:
        gdal.RasterizeLayer(raster, [1], layer, burn_values=[1])
    return raster.ReadAsArray()


def make_layers():
    data = json.loads(BOUNDARY.read_bytes())['features']
    city = next(feature for feature in data if feature['properties']['osm_id'] == BOUNDARY_ID)
    districts = sorted((f for f in data if f is not city), key=lambda f: f['properties']['name'])
    assert len({f['properties']['name'] for f in districts}) == 25
    refs = [osr.SpatialReference() for _ in range(2)]
    for ref, code in zip(refs, [4326, 5186]):
        ref.ImportFromEPSG(code)
        ref.SetAxisMappingStrategy(osr.OAMS_TRADITIONAL_GIS_ORDER)
    transform = osr.CoordinateTransformation(*refs)
    vectors = ogr.GetDriverByName('Memory').CreateDataSource('')
    clip = vectors.CreateLayer('city', refs[1])
    district_layer = vectors.CreateLayer('districts', refs[1])
    district_layer.CreateField(ogr.FieldDefn('district', ogr.OFTInteger))

    def add(layer, record, value=None):
        geometry = ogr.CreateGeometryFromJson(json.dumps(record['geometry']))
        geometry.Transform(transform)
        assert geometry.IsValid()
        feature = ogr.Feature(layer.GetLayerDefn())
        feature.SetGeometry(geometry)
        if value is not None:
            feature.SetField('district', value)
        layer.CreateFeature(feature)

    add(clip, city)
    for index, district in enumerate(districts, 1):
        add(district_layer, district, index)
    return vectors, clip, district_layer, city, districts


def city_statistics(gradient, mask):
    values = gradient[mask & np.isfinite(gradient) & (gradient >= 0)]
    assert values.size > 0
    return {
        'valid_cells': int(values.size), 'nodata_cells': int(mask.sum() - values.size),
        'median_grade_pct': round(float(np.median(values)), 2),
        'p90_grade_pct': round(float(np.percentile(values, 90)), 2),
        'ten_pct_or_above_cells': int(np.count_nonzero(values >= 10)),
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('tiles', type=Path, help='Directory with the two original .tif tiles')
    parser.add_argument('--collected-at', required=True, help='Download timestamp or date in KST')
    options = parser.parse_args()
    gdal.UseExceptions()
    paths = [options.tiles / (name + '.tif') for name in TILES]
    for file, expected in zip(paths, TILES.values()):
        assert sha256(file.read_bytes()).hexdigest() == expected, file
    vectors, clip, district_layer, city, districts = make_layers()
    xmin, xmax, ymin, ymax = clip.GetExtent()
    mosaic = gdal.BuildVRT('/vsimem/seoul-source.vrt', [str(p) for p in paths])
    margin = GRID * 3
    grid = gdal.Warp('', mosaic, format='MEM', dstSRS='EPSG:5186', dstNodata=NODATA,
                     outputBounds=(xmin-margin, ymin-margin, xmax+margin, ymax+margin),
                     xRes=GRID, yRes=GRID, targetAlignedPixels=True, resampleAlg='bilinear')
    surface = gdal.DEMProcessing('', grid, 'slope', format='MEM', alg='Horn', slopeFormat='percent')
    gradient = surface.ReadAsArray()
    city_mask = rasterize(clip, grid) > 0
    district_ids = rasterize(district_layer, grid, 'district')
    stats = city_statistics(gradient, city_mask)
    stats['cells_without_district_polygon'] = int(np.count_nonzero(city_mask & (district_ids == 0)))
    rows = []
    for index, district in enumerate(districts, 1):
        rows.append({'district': district['properties']['name'], 'osm_district_id': district['properties']['osm_id'],
                     **city_statistics(gradient, city_mask & (district_ids == index))})
    assert sum(row['valid_cells'] + row['nodata_cells'] for row in rows) + stats['cells_without_district_polygon'] == int(city_mask.sum())
    csv_path = HERE / 'copernicus-surface-grade-districts.csv'
    with csv_path.open('w', encoding='utf-8', newline='') as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0]), lineterminator='\n')
        writer.writeheader()
        writer.writerows(rows)

    out = HERE / 'seoul-copernicus-surface-grade-pct-30m.tif'
    gradient[~city_mask | ~np.isfinite(gradient) | (gradient < 0)] = NODATA
    result = gdal.GetDriverByName('GTiff').Create(str(out), grid.RasterXSize, grid.RasterYSize, 1,
                                                 gdal.GDT_Float32, options=['COMPRESS=DEFLATE', 'PREDICTOR=3'])
    result.SetProjection(grid.GetProjection())
    result.SetGeoTransform(grid.GetGeoTransform())
    result.SetMetadata({'SOURCE': 'Copernicus GLO-30 DSM', 'ATTRIBUTION': ATTRIBUTION,
                        'METHOD': 'Horn 3x3 on bilinear 30 m grid', 'FIELD_VERIFIED': 'false',
                        'ROUTING_ELIGIBLE': 'false'})
    band = result.GetRasterBand(1)
    band.SetNoDataValue(NODATA)
    band.SetUnitType('percent')
    band.SetDescription('Terrain surface gradient, no sidewalk slope measurement')
    band.WriteArray(gradient)
    band = result = None
    report = {
        'source_product': 'Copernicus DEM GLO-30 DSM, 2021 release on AWS',
        'acquisition_date_of_individual_pixels': None,
        'collected_at_kst': options.collected_at,
        'source_url': 'https://registry.opendata.aws/copernicus-dem/',
        'tile_files': [{'name': p.name, 'bytes': p.stat().st_size, 'sha256': expected,
                        'url': f'https://copernicus-dem-30m.s3.amazonaws.com/{p.stem}/{p.name}'}
                       for p, expected in zip(paths, TILES.values())],
        'boundary': {**city['properties'], 'sha256': sha256(BOUNDARY.read_bytes()).hexdigest(),
                     'districts': len(districts)},
        'source_horizontal_crs': 'EPSG:4326', 'vertical_datum': 'EGM2008 per product documentation',
        'output_horizontal_crs': 'EPSG:5186', 'resolution_m': GRID,
        'method': 'Bilinear projection then Horn 3×3 steepest local surface gradient, in percent. 30m cell centers used for boundary clipping.',
        'field_verified': False, 'routing_eligible': False, 'new_slope_values_promoted': 0,
        'statistics': stats,
        'outputs': {p.name: sha256(p.read_bytes()).hexdigest() for p in [out, csv_path]},
        'attribution': ATTRIBUTION,
    }
    (HERE / 'copernicus-surface-grade-source.json').write_text(json.dumps(report, ensure_ascii=False, indent=2) + '\n')
    print(json.dumps(stats))


if __name__ == '__main__':
    main()
