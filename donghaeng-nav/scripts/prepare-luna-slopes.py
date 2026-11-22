"""Extract a display-only beta slope layer around the apartment frontage."""

from collections import Counter
from hashlib import sha256
import json
import math
from pathlib import Path
import re

from osgeo import ogr, osr


ROOT = Path(__file__).resolve().parents[1]
DIST = ROOT / 'dist'
FRONTAGE_BUFFER_M = 65
APARTMENT = 'osm:way/379761187'
FOOT_ALLOWED = {'yes', 'designated', 'permissive'}
FORBIDDEN = {'no', 'private', 'customers', 'permit'}


def read(name):
    return json.loads((DIST / name).read_bytes())


def main():
    ogr.UseExceptions()
    refs = []
    for code in (4326, 5186):
        ref = osr.SpatialReference()
        ref.ImportFromEPSG(code)
        ref.SetAxisMappingStrategy(osr.OAMS_TRADITIONAL_GIS_ORDER)
        refs.append(ref)
    project = osr.CoordinateTransformation(*refs)
    apartment = next(f for f in read('data/accessibility/seoul/seoul-facilities.geojson')['features']
                     if f['properties'].get('id') == APARTMENT)
    polygon = ogr.CreateGeometryFromJson(json.dumps(apartment['geometry']))
    polygon.Transform(project)
    centroid = polygon.Centroid()
    ring = polygon.GetGeometryRef(0).GetPoints()
    frontages = ogr.Geometry(ogr.wkbMultiLineString)
    for a, b in zip(ring, ring[1:]):
        dx, dy = b[0] - a[0], b[1] - a[1]
        x, y = (a[0] + b[0]) / 2 - centroid.GetX(), (a[1] + b[1]) / 2 - centroid.GetY()
        if (x < 0 and abs(dy) >= abs(dx)) or (y < 0 and abs(dx) >= abs(dy)):
            edge = ogr.Geometry(ogr.wkbLineString)
            edge.AddPoint_2D(*a[:2])
            edge.AddPoint_2D(*b[:2])
            frontages.AddGeometry(edge)
    assert frontages.GetGeometryCount() >= 3

    graph_raw = (DIST / 'map-data.json').read_bytes()
    graph = json.loads(graph_raw)
    terrain = read('terrain-data.json')
    assert terrain['meta']['graph_sha256'] == sha256(graph_raw).hexdigest()
    assert terrain['meta']['field_verified'] is False
    info = terrain['screening']['edges']
    nodes = {e['id']: [e['lat'], e['lon']] for e in graph['elements'] if e['type'] == 'node'}
    projected = {key: project.TransformPoint(ll[1], ll[0])[:2] for key, ll in nodes.items()}
    access = read('data/precision/access-reports.json')['reports']
    bridge_ways = {way for record in access if record.get('betaLowerSlopeAssumption') for way in record['osmBridgeWays']}
    segments = []
    seen = set()
    for way in graph['elements']:
        if way['type'] != 'way':
            continue
        tags = way.get('tags', {})
        highway = tags.get('highway')
        if highway not in {'footway', 'path', 'pedestrian', 'steps', 'residential', 'service', 'living_street', 'unclassified', 'cycleway'}:
            continue
        if tags.get('foot') in FORBIDDEN or tags.get('access') in FORBIDDEN:
            continue
        if highway == 'cycleway' and tags.get('foot') not in FOOT_ALLOWED:
            continue
        for a, b in zip(way['nodes'], way['nodes'][1:]):
            if a not in projected or b not in projected:
                continue
            x, y = ((v + w) / 2 for v, w in zip(projected[a], projected[b]))
            pt = ogr.Geometry(ogr.wkbPoint)
            pt.AddPoint_2D(x, y)
            bridge = way['id'] in bridge_ways
            if not bridge and (pt.Distance(frontages) > FRONTAGE_BUFFER_M or pt.Within(polygon)):
                continue
            edge = '-'.join(sorted(map(str, (a, b))))
            if edge in seen:
                continue
            seen.add(edge)
            details = info.get(edge, {})
            kind = details.get('kind')
            low, high = details.get('minPercent'), details.get('maxPercent')
            grade = None
            if bridge:
                kind = 'bridge_assumption'
            elif kind == 'structure_unresolved':
                kind = 'unknown'
            else:
                registered = re.fullmatch(r'([+-]?(?:\d+(?:\.\d+)?|\.\d+))\s*%', tags.get('incline', ''))
                if registered:
                    grade = [abs(float(registered[1]))] * 2
                    kind = 'registered'
                elif all(isinstance(value, (int, float)) and math.isfinite(value) for value in (low, high)) and 0 <= low <= high:
                    grade = [low, high]
                    kind = 'estimated'
                else:
                    kind = 'unknown'
            segments.append({'edge': edge, 'way': way['id'], 'name': '육교' if bridge else tags.get('name', '보행로'),
                             'coordinates': [nodes[a], nodes[b]], 'kind': kind, 'grade': grade})
    assert any(s['grade'] for s in segments) and any(s['kind'] == 'bridge_assumption' for s in segments)
    payload = {'schema': 'donghaeng-luna-demo-slopes-v1', 'display_only': True, 'routing_eligible': False,
               'field_verified': False, 'focus': apartment['properties']['display_coordinates'][::-1], 'segments': segments}
    dest = DIST / 'data/terrain/luna-demo-slopes.json'
    dest.write_text(json.dumps(payload, ensure_ascii=False, separators=(',', ':')) + '\n')
    print(json.dumps(Counter(s['kind'] for s in segments)))


if __name__ == '__main__':
    main()
