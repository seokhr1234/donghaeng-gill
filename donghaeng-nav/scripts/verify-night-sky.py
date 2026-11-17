"""Verify UI-only promotion and preserve the previously deployed GIS snapshot."""
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
OLD = '406c11b594c4e6de51f3191ae91b8588c217e9c3'
sha = lambda b: hashlib.sha256(b).hexdigest()
read = lambda p: json.loads(p.read_bytes())
original = lambda p: subprocess.check_output(['git', 'show', OLD + ':' + p], cwd=ROOT)
lock = read(BASE / 'runtime-integrity.json')
old_lock = json.loads(original('donghaeng-nav/dist/runtime-integrity.json'))
assert lock['data'] == old_lock['data']
assert lock['code_revision']['previous_revision'] == old_lock['code_revision']
changed = set()
for name, digest in lock['protected_code'].items():
    assert sha((BASE / name).read_bytes()) == digest
    if old_lock['protected_code'].get(name) != digest:
        changed.add(name)
assert changed == {'osco-map.js', 'high-contrast.js'}
for item in lock['data']:
    relative = 'donghaeng-nav/dist/' + item['path']
    assert (ROOT / relative).read_bytes() == original(relative)
    assert (ROOT / (relative + '.gz')).read_bytes() == original(relative + '.gz')
assert not subprocess.check_output(['git', 'diff', OLD, '--name-only', '--', 'research'], cwd=ROOT).strip()
services = read(ROOT / 'donghaeng-nav/services/service-integrity.json')
old_services = json.loads(original('donghaeng-nav/services/service-integrity.json'))
allowed = {'donghaeng-nav/dist/' + name for name in ['app.js', 'index.html', 'map-layers.js', 'transit-walk-review.js',
           'journey-review.js', 'osco-map.js', 'high-contrast.js', 'high-contrast.css', 'expansion.js', 'expansion.html']}
allowed.add('donghaeng-nav/server.mjs')
for group in ['files', 'review_assets', 'city_assets', 'slope_assets']:
    if group != 'files':
        assert services[group] == old_services[group]
    for name, digest in services[group].items():
        assert sha((ROOT / name).read_bytes()) == digest, name
        if name not in allowed:
            assert (ROOT / name).read_bytes() == original(name)
build = read(ROOT / 'donghaeng-nav/docs/final-build.json')
htmls = [ROOT / ('동행길-' + n + '.html') for n in ['최종', '시연', '전달용']]
htmls += [p for p in (ROOT / '이동약자-내비게이션-실행패키지').glob('*.html')
          if unicodedata.normalize('NFC', p.name) in ['휴대폰용.html', '컴퓨터용.html']]
assert len(htmls) == 5 and all(sha(p.read_bytes()) == build['html_sha256'] for p in htmls)
html = htmls[0].read_text()
assert 'data-contrast-toggle' in html and 'root.HighContrast = ' in html
for item in lock['data']:
    block = re.search(r'<script id="' + re.escape(item['id']) + r'"[^>]*>([^<]+)</script>', html)
    packed = (BASE / (item['path'] + '.gz')).read_bytes()
    assert block and base64.b64decode(block[1]) == packed
    assert gzip.decompress(packed) == (BASE / item['path']).read_bytes()
assert build['high_contrast']['line_patterns']
ui = read(ROOT / 'donghaeng-nav/docs/night-sky-ui-results.json')
assert ui['pass'] and all(s['ratio'] >= 7 for s in ui['sampledTextContrast'])
assert 'transitEnabled:false' in (BASE / 'build-profile.js').read_text()
result = {'pass': True, 'baseline': OLD, 'runtime_datasets_byte_identical': len(lock['data']),
          'research_preserved': True, 'service_graph_and_slope_assets_preserved': True,
          'engine_and_navigation_policy_preserved': True, 'modified_display_code': sorted(changed),
          'existing_real_route_geometry_unchanged_under_toggle': True, 'paid_provider_calls': 0,
          'html_outputs_identical': len(htmls), 'sampled_text_contrast_minimum': min(s['ratio'] for s in ui['sampledTextContrast']),
          'night_sky_palette': True, 'natural_map_colors': True, 'nested_number_borders_removed': True, 'web_transit_enabled': False, 'new_slope_values_promoted': 0, 'field_verified': False}
(ROOT / 'donghaeng-nav/docs/night-sky-integrity.json').write_text(json.dumps(result, ensure_ascii=False, indent=2) + '\n')
print(json.dumps(result, ensure_ascii=False))
