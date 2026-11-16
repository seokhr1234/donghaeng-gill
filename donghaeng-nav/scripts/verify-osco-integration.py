"""Check promotion against the preserved research commit without weakening GIS locks."""
from pathlib import Path
import base64
import gzip
import hashlib
import json
import re
import subprocess
import unicodedata

ROOT = Path(__file__).resolve().parents[2]
BASE = ROOT / 'donghaeng-nav/dist'
OLD = '9f1dd30'
sha = lambda b: hashlib.sha256(b).hexdigest()
read = lambda p: json.loads(p.read_bytes())
original = lambda p: subprocess.check_output(['git', 'show', OLD + ':' + p], cwd=ROOT)
lock = read(BASE / 'runtime-integrity.json')
before = json.loads(original('donghaeng-nav/dist/runtime-integrity.json'))
assert lock['data'][:len(before['data'])] == before['data']
for item in before['data']:
    p = 'donghaeng-nav/dist/' + item['path']
    assert (ROOT / p).read_bytes() == original(p)
    assert (ROOT / (p + '.gz')).read_bytes() == original(p + '.gz')
changed = []
for name, digest in lock['protected_code'].items():
    assert sha((BASE / name).read_bytes()) == digest
    if before['protected_code'].get(name) != digest:
        changed.append(name)
assert set(changed) == {'app.js', 'map-layers.js', 'osco-map.js'}
service_path = ROOT / 'donghaeng-nav/services/service-integrity.json'
services = read(service_path)
previous_services = json.loads(original(str(service_path.relative_to(ROOT))))
for group in ['review_assets', 'city_assets', 'slope_assets']:
    assert services[group] == previous_services[group]
for group in ['files', 'review_assets', 'city_assets', 'slope_assets']:
    for path, digest in services[group].items():
        assert sha((ROOT / path).read_bytes()) == digest, path
        if group != 'files' or path not in {
            'donghaeng-nav/dist/app.js', 'donghaeng-nav/dist/index.html',
            'donghaeng-nav/dist/map-layers.js', 'donghaeng-nav/dist/osco-map.js', 'donghaeng-nav/dist/osco-map.css',
            'donghaeng-nav/server.mjs',
        }:
            assert (ROOT / path).read_bytes() == original(path), path
server = 'donghaeng-nav/server.mjs'
expected_server = original(server).decode().replace('trip-questions|map-layers|region-client', 'trip-questions|map-layers|osco-map|region-client')
expected_server = expected_server.replace(r'(?:style|leaflet|expansion|transit)\.css', r'(?:style|leaflet|expansion|transit|osco-map)\.css')
expected_server = expected_server.replace(r'data\/terrain\/evidence\.json', r'data\/osco\/(?:info|context)\.json|data\/terrain\/evidence\.json')
assert (ROOT / server).read_text() == expected_server
research = ROOT / 'research/accessibility/cheongju-osco-2026-11-16'
context = read(BASE / 'data/osco/context.json')
assert context['display_only'] and not context['field_verified'] and not context['routing_eligible']
for kind, features in context['layers'].items():
    assert features == read(research / ('derived/osm-' + kind + '.geojson'))['features']
info = read(BASE / 'data/osco/info.json')
evidence = read(research / 'primary-evidence.json')
for key in ['venue', 'bf_certificate', 'indoor_reference_plan', 'parking_claims']:
    assert info[key] == evidence[key]
assert not info['routing_eligible'] and not info['field_verified'] and info['new_slope_values_promoted'] == 0
assert not subprocess.check_output(['git', 'diff', OLD, '--name-only', '--', 'research'], cwd=ROOT).strip()
build = read(ROOT / 'donghaeng-nav/docs/final-build.json')
htmls = [ROOT / ('동행길-' + name + '.html') for name in ['최종', '시연', '전달용']]
htmls += [p for p in (ROOT / '이동약자-내비게이션-실행패키지').glob('*.html')
          if unicodedata.normalize('NFC', p.name) in ['휴대폰용.html', '컴퓨터용.html']]
assert len(htmls) == 5 and all(sha(p.read_bytes()) == build['html_sha256'] for p in htmls)
html = htmls[0].read_text()
for item in lock['data']:
    raw = (BASE / item['path']).read_bytes()
    assert sha(raw) == item['sha256']
    packed = (BASE / (item['path'] + '.gz')).read_bytes()
    assert gzip.decompress(packed) == raw
    block = re.search(r'<script id="' + re.escape(item['id']) + r'"([^>]*)>([^<]+)</script>', html)
    assert block and base64.b64decode(block[2]) == packed
    if item['id'] == 'bundled-osco-context':
        assert 'data-lazy="true"' in block[1]
assert build['osco_research']['display_only'] and not build['osco_research']['routing_eligible']
assert 'transitEnabled:false' in (BASE / 'build-profile.js').read_text()
assert 'initialArea:\'osco\'' in (ROOT / 'donghaeng-nav/mobile/scripts/prepare-web.mjs').read_text()
for name in ['osco-map-ui-results.json', 'web-walk-results.json', 'city-map-ui-results.json']:
    assert read(ROOT / 'donghaeng-nav/docs' / name)['pass']
result = {'pass': True, 'base_commit': OLD, 'previous_runtime_datasets_byte_identical': len(before['data']),
          'original_research_preserved': True, 'source_osm_geometry_tags_versions_preserved': True,
          'existing_graph_and_slope_assets_preserved': True, 'protected_code_changes': changed,
          'official_evidence_matches_research': True, 'municipal_and_secondary_geometry_published': False,
          'html_outputs_identical': len(htmls), 'runtime_hashes_checked': True,
          'osco_context_lazy_in_standalone': True, 'new_slope_values_promoted': 0,
          'osco_walking_routing_enabled': False, 'field_verified': False}
(ROOT / 'donghaeng-nav/docs/osco-integration-integrity.json').write_text(json.dumps(result, ensure_ascii=False, indent=2) + '\n')
print(json.dumps(result, ensure_ascii=False))
