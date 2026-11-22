#!/usr/bin/env python3
"""Audit OSM incline coverage and derive a Copernicus surface-slope research raster."""

from collections import Counter
import gzip
from hashlib import sha256
import json
from pathlib import Path

import numpy as np
from osgeo import gdal, osr


HERE = Path(__file__).resolve().parent
RESEARCH = HERE.parent
SCOPE = RESEARCH / 'osco-seoul-2026-11-21/osco/osm'
ORIGINAL = RESEARCH / 'cheongju-osco-2026-11-16'
CLIP = ORIGINAL / 'derived/osco-context-dem30m.tif'
PIXEL_METERS = 30
RADII_METERS = (1000, 3000)
NODATA = -9999
ATTRIBUTION = ('Produced using Copernicus WorldDEM-30 © DLR e.V. 2010-2014 and '
               '© Airbus Defence and Space GmbH 2014-2018 provided under COPERNICUS '
               'by the European Union and ESA; all rights reserved.')


def read(path):
    return json.loads(path.read_bytes())


def osm_audit():
    summary = read(SCOPE / 'summary.json')
    sources = {item['path']: item['sha256'] for item in summary['assets']}
    coverage = {}
    for name in ('pedestrian', 'road_context', 'access'):
        path = SCOPE / f'osm-{name}.geojson.gz'
        archive = path.read_bytes()
        assert sha256(archive).hexdigest() == sources[path.name]
        features = json.loads(gzip.decompress(archive))['features']
        coverage[name] = {}
        for label, selected in [
            ('bbox', features),
            *((f'{radius}m', [f for f in features if radius in f['properties']['within_straight_line_m']])
              for radius in RADII_METERS),
        ]:
            values = Counter(f['properties']['tags']['incline'] for f in selected
                             if 'incline' in f['properties']['tags'])
            coverage[name][label] = {'registered_objects': len(selected), 'incline_tags': dict(sorted(values.items()))}
    return summary['source_metadata'], coverage


def surface_slope(reference):
    gdal.UseExceptions()
    geodetic = osr.SpatialReference()
    projected = osr.SpatialReference()
    geodetic.ImportFromEPSG(4326)
    projected.ImportFromEPSG(5186)
    geodetic.SetAxisMappingStrategy(osr.OAMS_TRADITIONAL_GIS_ORDER)
    projected.SetAxisMappingStrategy(osr.OAMS_TRADITIONAL_GIS_ORDER)
    convert = osr.CoordinateTransformation(geodetic, projected)
    x, y, _ = convert.TransformPoint(*reference)
    radius = max(RADII_METERS)
    buffer = radius + 3 * PIXEL_METERS
    grid = gdal.Warp('', str(CLIP), format='MEM', dstSRS='EPSG:5186', xRes=PIXEL_METERS, yRes=PIXEL_METERS,
                     dstNodata=NODATA, resampleAlg='bilinear', outputBounds=(x-buffer, y-buffer, x+buffer, y+buffer),
                     targetAlignedPixels=True)
    raster = gdal.DEMProcessing('', grid, 'slope', format='MEM', alg='Horn', slopeFormat='percent')
    slope = raster.ReadAsArray()
    gt = grid.GetGeoTransform()
    x_grid = gt[0] + (np.arange(grid.RasterXSize) + .5) * gt[1]
    y_grid = gt[3] + (np.arange(grid.RasterYSize) + .5) * gt[5]
    distance_sq = (y_grid[:, None] - y)**2 + (x_grid[None, :] - x)**2
    valid = np.isfinite(slope) & (slope >= 0)
    counts = {}
    for distance in RADII_METERS:
        inside = distance_sq <= distance**2
        values = slope[inside & valid]
        assert values.size > 0
        counts[f'{distance}m'] = {
            'cells': int(values.size), 'cells_without_value': int(np.count_nonzero(inside & ~valid)),
            'median_percent': round(float(np.median(values)), 2),
            'p90_percent': round(float(np.percentile(values, 90)), 2),
        }
    slope[~valid | (distance_sq > radius**2)] = NODATA
    output = HERE / 'osco-copernicus-surface-slope-percent.tif'
    dst = gdal.GetDriverByName('GTiff').Create(str(output), grid.RasterXSize, grid.RasterYSize,
                                              1, gdal.GDT_Float32, options=['COMPRESS=DEFLATE', 'PREDICTOR=3'])
    dst.SetGeoTransform(gt)
    dst.SetProjection(projected.ExportToWkt())
    dst.SetMetadata({'SOURCE': 'Copernicus GLO-30 DSM', 'METHOD': 'Horn 3x3 on bilinear 30m grid',
                     'ATTRIBUTION': ATTRIBUTION, 'ROUTING_ELIGIBLE': 'false', 'FIELD_VERIFIED': 'false'})
    band = dst.GetRasterBand(1)
    band.SetNoDataValue(NODATA)
    band.SetUnitType('percent')
    band.SetDescription('DSM surface gradient, not a sidewalk or route grade')
    band.WriteArray(slope)
    band = dst = None
    return output, counts


def main():
    osm, coverage = osm_audit()
    extraction = read(ORIGINAL / 'dem-extraction-results.json')
    validation = read(ORIGINAL / 'dem-validation.json')
    source = next(item for item in read(ORIGINAL / 'sources.json') if item['id'] == extraction['sourceId'])
    assert extraction['surfaceModel'] is True and validation['field_verified'] is False
    reference = osm['reference_point_lon_lat']
    output, stats = surface_slope(reference)
    result = {
        'field_verified': False, 'routing_eligible': False, 'new_slope_values_promoted': 0,
        'reference_lonlat': reference,
        'osm': {'source_as_of': osm['source_as_of'], 'collected_at_kst': osm['retrieved_at_kst'],
                'url': osm['source_url'], 'source_crs': osm['source_crs'], 'coverage': coverage},
        'copernicus': {
            'url': extraction['sourceUrl'], 'source_collection': 'Copernicus DEM 2021 release (AWS)',
            'local_tile_acquisition_date': None, 'original_collected_at_kst': source['requested_at_kst'],
            'source_crs': extraction['sourceCrs'], 'vertical_datum': extraction['verticalDatum'],
            'source_sha256': extraction['sourceSha256'], 'input_clip_sha256': sha256(CLIP.read_bytes()).hexdigest(),
            'derived_crs': 'EPSG:5186', 'derived_pixel_spacing_m': PIXEL_METERS,
            'method': 'Bilinear reprojection followed by a 3x3 Horn local surface gradient in percent',
            'derived_raster': output.name, 'derived_sha256': sha256(output.read_bytes()).hexdigest(),
            'raster_summary': stats, 'attribution': ATTRIBUTION,
        },
    }
    (HERE / 'slope-audit.json').write_text(json.dumps(result, indent=2, ensure_ascii=False) + '\n')
    print(json.dumps(stats))


if __name__ == '__main__':
    main()
