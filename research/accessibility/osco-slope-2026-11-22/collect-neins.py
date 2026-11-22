#!/usr/bin/env python3
"""Record the public NEINS viewer's 5 m DEM-derived point classes."""

from datetime import datetime
from hashlib import sha256
import json
from math import asinh, radians, tan
from pathlib import Path
from urllib.parse import urlencode
from urllib.request import Request, urlopen
from zoneinfo import ZoneInfo


HERE = Path(__file__).resolve().parent
PACKET = HERE.parent / 'osco-seoul-2026-11-21/osco'
ORIGIN = 'https://webgis.neins.go.kr'
VIEWER = ORIGIN + '/map.do'
POINT_QUERY = ORIGIN + '/proxy/proxy.do?url=/proxy/raster/ghFeature'
KST = ZoneInfo('Asia/Seoul')


def main():
    records = json.loads((PACKET / 'anchors/source-review.json').read_bytes())
    park = json.loads((PACKET / 'rest-evidence/kto-osong-reference-points.geojson').read_bytes())['features'][0]
    assert park['properties']['name'] == '오송호수공원'
    locations = [records['venue'], *records['osm']['anchors'], {
        'name': park['properties']['name'], 'coordinates': park['geometry']['coordinates'],
        'coordinate_role': park['properties']['coordinate_role'],
        'source_url': park['properties']['source_url'],
    }]
    samples = []
    for place in locations:
        lon, lat = map(radians, place['coordinates'])
        x, y = (6378137 * lon, 6378137 * asinh(tan(lat)))
        params = {'featureType': 'Point', 'coordinate': f'POINT({x:.6f} {y:.6f})', 'epsgCd': 'EPSG:3857',
                  'scaleValue': '5000', 'layerAnalysisGroupCd': 'AG007', 'analysisType': 'gradient'}
        sample = {key: place[key] for key in ('name', 'coordinates', 'coordinate_role', 'source_url')}
        sample['queried_at_kst'] = datetime.now(KST).isoformat(timespec='seconds')
        sample['request_point_epsg3857'] = params['coordinate']
        request = Request(POINT_QUERY, data=urlencode(params).encode(), headers={
            'Referer': VIEWER, 'Origin': ORIGIN, 'X-Requested-With': 'XMLHttpRequest'})
        try:
            with urlopen(request, timeout=12) as response:
                raw = response.read()
                sample['http_status'] = response.status
            sample['response_sha256'] = sha256(raw).hexdigest()
            info = json.loads(raw)['info']
            assert (info['featureType'], info['epsgCd'], info['scaleValue']) == ('Point', 'EPSG:3857', '5000')
            [result] = info['mapDataList']
            sample.update({'class_code': result['grade'], 'class_label': result['name']})
        except (OSError, ValueError, KeyError, TypeError, AssertionError) as exc:
            sample['error'] = type(exc).__name__
        samples.append(sample)
    report = {
        'provider': '환경부 국토환경성평가지도', 'viewer_url': VIEWER, 'request_url': POINT_QUERY,
        'provider_dem_vintage': 2022, 'provider_dem_cell_size_m': 5,
        'response_type': 'terrain slope class in degrees, no exact slope',
        'horizontal_crs': 'EPSG:4326 reference / EPSG:3857 request', 'vertical_datum': None,
        'road_surface_measured': False, 'field_verified': False, 'routing_eligible': False, 'samples': samples,
    }
    (HERE / 'neins-point-slope-classes.json').write_text(json.dumps(report, indent=2, ensure_ascii=False) + '\n')
    print([(s['name'], s.get('class_label'), s.get('error')) for s in samples])


if __name__ == '__main__':
    main()
