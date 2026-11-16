"""Promote licensed OSM geometry and attributed venue facts for display only.

No municipal/mirror data, graph edges, indoor georeferencing or new slopes.
Input hashes are bound to the preserved research packet, not silently refreshed.
"""
from pathlib import Path
import hashlib
import json

ROOT = Path(__file__).resolve().parents[2]
RESEARCH = ROOT / 'research/accessibility/cheongju-osco-2026-11-16'
OUT = ROOT / 'donghaeng-nav/dist/data/osco'
sha = lambda b: hashlib.sha256(b).hexdigest()
read = lambda p: json.loads(p.read_bytes())


def build():
    verified = read(RESEARCH / 'packet-verification.json')
    assert verified['pass'] and not verified['field_verified']
    assets = {a['file']: a for a in verified['artifacts']}
    source_records = {r['id']: r for r in read(RESEARCH / 'sources.json')}
    evidence = read(RESEARCH / 'primary-evidence.json')
    review = read(RESEARCH / 'geometry-and-completeness-review.json')
    sources = []
    for ident in ['geofabrik-korea-261115-pbf', 'gallery-directions', 'bf-osco-detail-main',
                  'bf-osco-excel', 'osco-facility-pdf', 'osco-parking', 'osco-parking-plan-image', 'osco-traffic']:
        s = source_records[ident]
        assert s['response_complete'] and s['requested_resource_verified']
        sources.append({k: s.get(k) for k in ['id', 'url', 'sha256', 'source_as_of', 'collected_at_utc',
                                           'requested_at_kst', 'page_modified_at', 'declared_source_crs']})
    layers = {}
    inputs = []
    for layer in ['roads', 'buildings', 'access_points', 'transport', 'facilities']:
        relative = 'derived/osm-' + layer + '.geojson'
        raw = (RESEARCH / relative).read_bytes()
        assert sha(raw) == assets[relative]['sha256']
        assert not review[layer]['invalid_geometries']
        fc = json.loads(raw)
        assert fc['source_metadata']['license'] == 'ODbL-1.0'
        assert fc['source_metadata']['field_verified'] is False
        assert fc['source_metadata']['routing_eligible'] is False
        layers[layer] = fc['features']  # Exact original coordinates, tags, versions and timestamps.
        inputs.append({'path': relative, 'sha256': sha(raw), 'features': len(fc['features'])})
    venue = evidence['venue']
    assert venue['building_contains_official_representative_point']
    station = next(f for f in layers['transport'] if f['id'] == 'node/368637868')
    def place(ident, name, coords, address, source):
        return {'id': ident, 'name': name, 'll': [coords[1], coords[0]], 'address': address,
                'sourceUrl': source, 'approximate': True, 'coordinateRole': 'representative_not_verified_entrance'}
    info = {
        'schema': 'donghaeng-osco-info-v1', 'field_verified': False, 'routing_eligible': False,
        'display_only': True, 'bounds_lonlat': [127.28, 36.59, 127.39, 36.67],
        'core_bounds_lonlat': [127.315, 36.61, 127.35, 36.64],
        'places': [place('osco:venue', venue['name'], venue['representative_point_lonlat'], venue['address'],
                         source_records['gallery-directions']['url']),
                   place(station['id'], '오송역 · OSM 대표점', station['geometry']['coordinates'],
                         '철도역 등록 대표점 · 실제 출입구 미확인', 'https://www.openstreetmap.org/' + station['id'])],
        'venue': venue, 'bf_certificate': evidence['bf_certificate'],
        'indoor_reference_plan': evidence['indoor_reference_plan'], 'parking_claims': evidence['parking_claims'],
        'sources': sources, 'osm_source_metadata': fc['source_metadata'],
        'osm_layer_counts': {k: len(v) for k, v in layers.items()},
        'not_published': ['municipal GIS: reuse terms unconfirmed', 'secondary shelters/toilets: source/licence unconfirmed'],
        'terrain_notice': '30m급 DSM은 보도 노면 경사가 아닙니다. 청주 주변의 새 경사값은 제공하지 않습니다.',
        'new_slope_values_promoted': 0,
    }
    context = {'schema': 'donghaeng-osco-context-v1', 'display_only': True, 'field_verified': False,
               'routing_eligible': False, 'source_metadata': info['osm_source_metadata'], 'layers': layers}
    OUT.mkdir(parents=True, exist_ok=True)
    outputs = []
    for name, data in [('info.json', info), ('context.json', context)]:
        raw = (json.dumps(data, ensure_ascii=False, separators=(',', ':')) + '\n').encode()
        (OUT / name).write_bytes(raw)
        outputs.append({'path': 'data/osco/' + name, 'sha256': sha(raw), 'bytes': len(raw)})
    result = {'pass': True, 'inputs': inputs, 'outputs': outputs, 'source_geometry_and_tags_preserved': True,
              'municipal_or_secondary_geometry_published': False, 'new_routing_edges': 0,
              'new_slope_values_promoted': 0, 'field_verified': False, 'routing_eligible': False}
    (ROOT / 'donghaeng-nav/docs/osco-map-data-results.json').write_text(json.dumps(result, ensure_ascii=False, indent=2) + '\n')
    print(json.dumps({'pass': True, 'layers': info['osm_layer_counts'], 'outputs': outputs}))


if __name__ == '__main__':
    build()
