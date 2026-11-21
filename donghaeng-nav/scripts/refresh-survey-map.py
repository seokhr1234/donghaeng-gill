"""Publish verified OSM observations as display-only map layers."""

import gzip
import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
RESEARCH = ROOT / 'research/accessibility/osco-seoul-2026-11-21'
OUTPUT = ROOT / 'donghaeng-nav/dist/data/osco'
SOURCE_ID = 'geofabrik-korea-261120-pbf'


def read(path):
    return json.loads(path.read_bytes())


def digest(raw):
    return hashlib.sha256(raw).hexdigest()


def local_layers():
    data = read(RESEARCH / 'verification.json')
    assert data['field_verified'] is False and data['routing_eligible'] is False
    assert 'gzip checksums' in data['checks']
    osco = read(RESEARCH / 'osco/osm/summary.json')
    seoul = read(RESEARCH / 'seoul/osm/summary.json')
    city = read(RESEARCH / 'seoul/osm/seoul-citywide-summary.json')
    inputs = {}

    def extract(area, layer, summary, *, radius=None, polygons=False):
        dataset = f'{layer}.geojson.gz'
        path = RESEARCH / area / 'osm' / dataset
        archive = path.read_bytes()
        record = next(item for item in summary if item['path'] == dataset)
        assert digest(archive) == record['sha256']
        collection = json.loads(gzip.decompress(archive))
        source = collection['source_metadata']
        assert source['source_as_of'] == osco['source_metadata']['source_as_of']
        assert source['license'] == 'ODbL-1.0'
        inputs[str(path.relative_to(RESEARCH))] = record['sha256']
        for feature in collection['features']:
            props = feature['properties']
            assert props['field_verified'] is False and props['routing_eligible'] is False
            if radius is not None and radius not in props['within_straight_line_m']:
                continue
            if polygons and feature['geometry']['type'] not in ('Polygon', 'MultiPolygon'):
                continue
            # Source geometry, IDs, object times and tags are unchanged. The
            # research archive retains node references and audit fields.
            yield {
                'type': 'Feature', 'id': feature['id'], 'geometry': feature['geometry'],
                'properties': {key: props[key] for key in ('tags', 'osm_version', 'osm_timestamp')},
            }

    def cheongju(name, **options):
        return list(extract('osco', 'osm-' + name, osco['assets'], **options))

    def wolgok(name, **options):
        return list(extract('seoul', 'osm-' + name, seoul['assets'], radius=3000, **options))

    def unique(features):
        return list({feature['id']: feature for feature in features}.values())

    layers = {
        'roads': cheongju('pedestrian'),
        'access_points': cheongju('access'),
        'transport': cheongju('transit'),
        'facilities': cheongju('support'),
        'rest': cheongju('rest'),
        'buildings': cheongju('buildings', polygons=True),
        'seoul_roads': wolgok('pedestrian'),
        'seoul_buildings': wolgok('buildings', polygons=True),
        'seoul_rest': list(extract('seoul', 'seoul-citywide-rest', city['citywide_assets'])),
    }
    assert len(layers['seoul_rest']) == city['layers']['rest']
    assert any(f['id'] == 'node/8213401393' for f in layers['access_points'])
    for kind, features in layers.items():
        assert features and len(features) == len(unique(features)), kind
    return osco['source_metadata'], seoul['source_metadata'], layers, inputs


def main():
    source, wolgok, layers, inputs = local_layers()
    info = read(OUTPUT / 'info.json')
    info['osm_source_metadata'] = source
    info['osm_layer_counts'] = {kind: len(features) for kind, features in layers.items()}
    info['seoul_reference_lonlat'] = wolgok['reference_point_lon_lat']
    # Keep official venue and earlier source records to preserve their provenance.
    info['sources'] = [item for item in info['sources'] if item['id'] != SOURCE_ID]
    info['sources'].insert(0, {
        'id': SOURCE_ID, 'url': source['source_url'], 'sha256': source['source_pbf_sha256'],
        'source_as_of': source['source_as_of'], 'requested_at_kst': source['retrieved_at_kst'],
        'declared_source_crs': source['source_crs'],
    })
    info['active_osm_source_id'] = SOURCE_ID
    context = {
        'schema': 'donghaeng-osco-context-v1', 'display_only': True, 'field_verified': False,
        'routing_eligible': False, 'source_metadata': source, 'layers': layers,
    }
    outputs = []
    for name, payload in [('info.json', info), ('context.json', context)]:
        raw = (json.dumps(payload, ensure_ascii=False, separators=(',', ':')) + '\n').encode()
        (OUTPUT / name).write_bytes(raw)
        outputs.append({'path': 'data/osco/' + name, 'sha256': digest(raw), 'bytes': len(raw)})
    report = {
        'pass': True, 'source_snapshot': source['source_as_of'], 'inputs': inputs, 'outputs': outputs,
        'counts': info['osm_layer_counts'], 'source_geometry_and_tags_preserved': True,
        'municipal_or_secondary_geometry_published': False, 'new_routing_edges': 0,
        'new_slope_values_promoted': 0, 'field_verified': False, 'routing_eligible': False,
    }
    (ROOT / 'donghaeng-nav/docs/survey-map-data-results-2026-11-22.json').write_text(
        json.dumps(report, ensure_ascii=False, indent=2) + '\n')
    print(json.dumps(report['counts'], ensure_ascii=False))


if __name__ == '__main__':
    main()
