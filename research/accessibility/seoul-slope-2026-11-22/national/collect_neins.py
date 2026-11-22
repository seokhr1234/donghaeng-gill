"""Check NEINS public point-analysis coverage at selected Seoul WGS84 points."""
from datetime import datetime
from hashlib import sha256
from math import asinh, radians, tan
from pathlib import Path
from urllib.error import HTTPError
from urllib.parse import urlencode
from urllib.request import Request, urlopen
from zoneinfo import ZoneInfo
import json

root = Path(__file__).resolve().parent
base = 'https://webgis.neins.go.kr'
viewer = base + '/map.do'
url = base + '/proxy/proxy.do?url=/proxy/raster/ghFeature'
tz = ZoneInfo('Asia/Seoul')
points = [
    ('jongno-south', '서울 도심 남측 시험점', 126.978, 37.5665),
    ('jongno-center', '종로 도심 시험점', 126.980, 37.573),
    ('namsan', '남산 일대 시험점', 126.98830, 37.55135),
    ('bukak', '북악산 일대 시험점', 126.98050, 37.59300),
    ('hangang-north', '한강 북측 저지대 시험점', 126.94438, 37.52767),
    ('gangnam', '강남 도심 시험점', 127.028, 37.498),
    ('hangang-water', '한강 수면 부근 비교점', 126.93590, 37.53193),
]
raw_dir = root / 'raw-neins'
raw_dir.mkdir(exist_ok=True)
samples = []
for point_id, label, lon, lat in points:
    x, y = 6378137 * radians(lon), 6378137 * asinh(tan(radians(lat)))
    params = {'featureType':'Point', 'coordinate':f'POINT({x:.6f} {y:.6f})', 'epsgCd':'EPSG:3857',
              'scaleValue':'5000', 'layerAnalysisGroupCd':'AG007', 'analysisType':'gradient'}
    rec = {'id':point_id, 'description':label, 'coordinates_epsg4326':[lon,lat],
           'query_wkt_epsg3857':params['coordinate'], 'queried_at_kst':datetime.now(tz).isoformat(timespec='seconds')}
    request = Request(url, data=urlencode(params).encode(), headers={
        'Referer':viewer, 'Origin':base, 'X-Requested-With':'XMLHttpRequest'})
    try:
        with urlopen(request, timeout=10) as response:
            raw = response.read()
            rec['http_status'] = response.status
            rec['response_content_type'] = response.headers.get('Content-Type')
        (raw_dir / f'{point_id}.json').write_bytes(raw)
        rec['sha256'] = sha256(raw).hexdigest()
        info = json.loads(raw)['info']
        assert (info['featureType'],info['epsgCd'], str(info['scaleValue']))==('Point','EPSG:3857','5000')
        classes = info['mapDataList']
        result, = classes
        rec.update(class_code=result['grade'],class_label_degrees=result['name'])
    except (OSError, KeyError, ValueError, TypeError, AssertionError) as e:
        rec['error'] = f'{type(e).__name__}: {e}'
        if isinstance(e, HTTPError):
            rec['http_status'] = e.code
    samples.append(rec)
report = {'provider':'기후에너지환경부·한국환경연구원 국토환경성평가지도','viewer_url':viewer,
          'source_url':'https://ecvam.neins.go.kr/board/faq/faqView.do?board_seq=270&pageIndex=1', 'query_url':url,
          'source_year_per_viewer':2022, 'grid_size_m_per_viewer':5, 'crs_request':'EPSG:3857',
          'analysis_type':'terrain inclination category in degrees; slope azimuth and longitudinal/cross slope unpublished',
          'observed_on_site':False, 'routing_eligible':False,
          'selection_note':'Analyst-selected test coordinates, not official entrances, traversable sidewalk points or a representative citywide sample.',
          'samples':samples}
(root / 'neins-seoul-sample.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n')
print([(r['id'], r.get('http_status'), r.get('class_label_degrees'), r.get('error')) for r in samples])
