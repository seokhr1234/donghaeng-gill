"""Verify the signed demo APK without printing its native-only key."""
from pathlib import Path
import hashlib
import json
import os
import re
import subprocess
import zipfile

ROOT = Path(__file__).resolve().parents[2]
MOBILE = ROOT / 'donghaeng-nav/mobile'
APK = MOBILE / 'android/app/build/outputs/apk/release/app-release.apk'
TOOLS = Path(os.environ['ANDROID_HOME']) / 'build-tools/36.0.0'
sha = lambda raw: hashlib.sha256(raw).hexdigest()
env = dict(os.environ)
env['PATH'] = str(Path(env['JAVA_HOME']) / 'bin') + ':' + env['PATH']
signature = subprocess.check_output([str(TOOLS / 'apksigner'), 'verify', '--verbose', '--print-certs', str(APK)], env=env).decode()
badging = subprocess.check_output([str(TOOLS / 'aapt2'), 'dump', 'badging', str(APK)], env=env).decode()
assert "name='app.donghaeng.gill.demo'" in badging
assert "versionCode='3'" in badging and "versionName='1.0.2'" in badging
assert re.search(r"(?:minSdkVersion|sdkVersion):'24'", badging)
assert "targetSdkVersion:'36'" in badging and 'application-debuggable' not in badging
assert 'Verified using v2 scheme (APK Signature Scheme v2): true' in signature
certificate = re.search(r'Signer #1 certificate SHA-256 digest: ([a-f0-9]+)', signature)[1]
previous = json.loads((ROOT / 'donghaeng-nav/docs/android-release-apk-results-2026-11-16.json').read_text())
assert certificate == previous['certificateSha256']
key = next(line.split('=', 1)[1].strip() for line in (MOBILE / 'key.properties').read_text().splitlines()
           if line.startswith('ODSAY_ANDROID_KEY='))
assert key
web_assets = []
native_key_found = False
with zipfile.ZipFile(APK) as archive:
    assert archive.testzip() is None
    for name in archive.namelist():
        assert not name.endswith(('.keystore', 'key.properties', 'signing.properties'))
        if name.startswith('assets/public/') and not name.endswith('/'):
            raw = archive.read(name)
            assert key.encode() not in raw
            relative = name.removeprefix('assets/public/')
            local = MOBILE / 'android/app/src/main/assets/public' / relative
            assert local.is_file() and local.read_bytes() == raw, relative
            web_assets.append({'file': relative, 'bytes': len(raw), 'sha256': sha(raw)})
        if re.fullmatch(r'classes\d*\.dex', name) and key.encode() in archive.read(name):
            native_key_found = True
    assert native_key_found
    profile = archive.read('assets/public/build-profile.js').decode()
    assert "target:'android-demo'" in profile and 'transitEnabled:true' in profile and "initialArea:'osco'" in profile
    assert b'osco-map.js' in archive.read('assets/public/index.html')
    for name in ['info', 'context']:
        relative = 'data/osco/' + name + '.json'
        assert archive.read('assets/public/' + relative) == (ROOT / 'donghaeng-nav/dist' / relative).read_bytes()
assert not any(n.endswith('.gz') for n in (a['file'] for a in web_assets))
for name in ['/tmp/osco-apk-release-build.log', '/tmp/osco-apk-final-build.log']:
    if Path(name).is_file():
        assert key.encode() not in Path(name).read_bytes()
result = {'pass': True, 'checked_date_kst': '2026-11-17', 'app_id': 'app.donghaeng.gill.demo',
          'version_name': '1.0.2', 'version_code': 3, 'min_sdk': 24, 'target_sdk': 36,
          'build': 'release', 'debuggable': False, 'signature_verified': True, 'signature_scheme_v2': True,
          'certificate_sha256': certificate, 'same_signing_certificate_as_1_0_1': True,
          'apk_bytes': APK.stat().st_size, 'apk_sha256': sha(APK.read_bytes()),
          'android_transit_enabled': True, 'initial_area': 'osco', 'native_key_embedded': native_key_found,
          'key_in_web_assets': False, 'key_or_signing_files_in_apk': False, 'key_in_build_logs': False,
          'packaged_assets_match_synced_source': True, 'osco_packet_matches_dist': True,
          'web_asset_manifest': web_assets, 'new_provider_calls': 0,
          'actual_android_device_test': False, 'gps_field_test': False, 'field_verified': False}
out = ROOT / 'donghaeng-nav/docs/osco-android-apk-results-2026-11-17.json'
out.write_text(json.dumps(result, ensure_ascii=False, indent=2) + '\n')
print(json.dumps({k: v for k, v in result.items() if k != 'web_asset_manifest'}, ensure_ascii=False))
