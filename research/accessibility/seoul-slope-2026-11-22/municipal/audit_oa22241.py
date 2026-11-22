from collections import Counter
from hashlib import file_digest
from pathlib import Path
from zipfile import ZipFile
import argparse, json, math
from datetime import datetime
from zoneinfo import ZoneInfo

from osgeo import gdal, ogr, osr

p = argparse.ArgumentParser()
p.add_argument('folder', type=Path, help='Directory containing oa1.zip, oa2.zip')
p.add_argument('boundaries', type=Path, help='Preserved Seoul + 25 district OSM GeoJSON')
args = p.parse_args()

gdal.UseExceptions()
ogr.UseExceptions()
gdal.SetConfigOption('SHAPE_ENCODING', 'CP949')

def authority(code):
    projection = osr.SpatialReference()
    projection.ImportFromEPSG(code)
    projection.SetAxisMappingStrategy(osr.OAMS_TRADITIONAL_GIS_ORDER)
    return projection

wgs84, legacy = authority(4326), authority(5174)
to_legacy = osr.CoordinateTransformation(wgs84, legacy)

def boundary(feature):
    geometry = ogr.CreateGeometryFromJson(json.dumps(feature['geometry']))
    geometry.AssignSpatialReference(wgs84)
    geometry.Transform(to_legacy)
    if not geometry.IsValid():
        geometry = geometry.MakeValid()
    return geometry

source = json.loads(args.boundaries.read_bytes())['features']
city = next(row for row in source if row['properties']['osm_id'] == 'relation/2297418')
districts = {row['properties']['name']: boundary(row) for row in source if row is not city}
assert len(districts) == 25
geo = boundary(city)

def format_extent(b):
    return dict(zip(['west','east','south','north'],b))

def layer_info(shp):
    dataset = ogr.Open(str(shp))
    layer = dataset.GetLayer(0)
    crs = layer.GetSpatialRef()
    crs.AutoIdentifyEPSG()
    assert crs.GetAuthorityCode(None) == '5174', str(shp)
    definition = layer.GetLayerDefn()
    fields = {}
    for i in range(definition.GetFieldCount()):
        fd = definition.GetFieldDefn(i)
        fields[fd.GetName()] = {'type': fd.GetTypeName(), 'width': fd.GetWidth(), 'precision':fd.GetPrecision()}
    height = Counter()
    equality = Counter()
    distinct_ufid = set()
    for row in layer:
        h = row.GetField('HEIGHT')
        if isinstance(h, (int, float)) and math.isfinite(h):
            height[h] += 1
        else:
            equality['height_missing'] += 1
        base_field = 'CONT' if shp.stem.startswith('N3L') else 'NUME'
        comparison = row.GetField(base_field)
        equality[base_field + ('_equals_HEIGHT' if h == comparison else '_differs_from_HEIGHT')] += 1
        distinct_ufid.add(row.GetField('UFID'))
    def inside(geometry):
        layer.SetSpatialFilter(geometry)
        layer.ResetReading()
        return sum(feature.GetGeometryRef().Intersects(geometry) for feature in layer if feature.GetGeometryRef())
    city_count = inside(geo)
    counts = {district: inside(polygon) for district, polygon in districts.items()}
    layer.SetSpatialFilter(None)
    return {
        'type': ogr.GeometryTypeToName(layer.GetGeomType()), 'fields': fields,
        'horizontal_crs': 'EPSG:5174', 'geom_extent': format_extent(layer.GetExtent()),
        'total_raw': layer.GetFeatureCount(), 'unique_ufid':len(distinct_ufid),
        'height_comparison': dict(equality), 'height_range': [min(height), max(height)],
        'height_distinct_values': len(height), 'seoul_boundary_intersections': city_count,
        'district_intersections': dict(sorted(counts.items())),
        'districts_with_at_least_one': sum(count > 0 for count in counts.values()),
    }

result = {
    'dataset_url': 'https://data.seoul.go.kr/dataList/OA-22241/F/1/datasetView.do',
    'source_reported_vintage': '2023년 기준 수치지형도', 'license_reported': 'KOGL type 1',
    'audited_at_kst': datetime.now(ZoneInfo('Asia/Seoul')).isoformat(),
    'boundaries_source': city['properties'].get('source_url'),
    'boundaries_source_as_of': city['properties'].get('source_as_of'),
    'boundary_intersection_note': 'Point or line intersects preserved OSM relation polygons. Border contour can count in several districts. Nonzero means presence, not dense or complete coverage.',
    'vertical_datum': None, 'field_verified': False, 'routing_eligible': False, 'files': {},
}

for seq in (1,2):
    file = args.folder / f'oa{seq}.zip'
    with file.open('rb') as fp:
        s = file_digest(fp, 'sha256').hexdigest()
    unpack = args.folder / f'oa{seq}-layers'
    unpack.mkdir(exist_ok=True)
    with ZipFile(file) as z:
        assert z.testzip() is None
        for n in z.namelist():
            if n.endswith(('.shp','.dbf','.prj','.shx','.xml','.txt','.cpg')): z.extract(n, unpack)
    result['files'][f'seq{seq}'] = {
        'url': f'https://datafile.seoul.go.kr/bigfile/iot/inf/nio_download.do?infId=OA-22241&infSeq=1&seq={seq}&useCache=false',
        'bytes': file.stat().st_size,'sha256':s, 'crc_valid':True,
        'layers': {p.stem: layer_info(p) for p in sorted(unpack.rglob('*.shp'))},
    }
out = args.folder / 'oa22241-25-district-audit.json'
out.write_text(json.dumps(result, ensure_ascii=False, indent=2) + '\n')
for seq, file in result['files'].items():
    for layer, item in file['layers'].items():
        print(seq, layer, item['total_raw'], item['seoul_boundary_intersections'],
              item['districts_with_at_least_one'], item['height_range'], item['height_comparison'])
