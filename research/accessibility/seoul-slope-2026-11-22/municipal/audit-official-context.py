"""Audit files retrieved from the Seoul Open Data portal and Gangnam's city notice."""
from collections import Counter
import hashlib
import json
from pathlib import Path
import re
import subprocess
import zipfile

from openpyxl import load_workbook


BASE = Path(__file__).parent
DATA_URL = 'https://datafile.seoul.go.kr/bigfile/iot/inf/nio_download.do'
GANGNAM_NOTICE = 'https://www.gangnam.go.kr/center/board/B_000282/1096692/view.do?keyfield=bdm_main_title&mid=MC080301&office=3220052&pgno=10'
GANGNAM_FILE = 'https://www.gangnam.go.kr/file/1/get/21f8716f-c46c-44c0-8a64-b948149465d4/download.do'


def checked(path, url, digest):
    path = BASE / path
    got = hashlib.sha256(path.read_bytes()).hexdigest()
    assert got == digest, (path, got)
    if zipfile.is_zipfile(path):
        with zipfile.ZipFile(path) as archive:
            assert archive.testzip() is None
    return {'file': path.name, 'url': url, 'http_status': 200, 'bytes': path.stat().st_size, 'sha256': got}


def report():
    entrance = checked(
        'entrance-spatial.zip', DATA_URL + '?infId=OA-21699&infSeq=3&seq=1&useCache=false',
        'cfcce59f1d61f6fd2393130b86a97a6b785f27134f1059f38451ba84fb82d933')
    entrance_dictionary = checked(
        'entrance-dictionary.hwpx', DATA_URL + '?infId=OA-21699&infSeq=3&seq=20&useCache=false',
        'e057f77b97faece8e8b48bef6a1deae552d437e771e144c929df18f54bb1fb35')
    with zipfile.ZipFile(BASE / entrance['file']) as archive:
        archive.extractall(BASE / 'entrance-spatial', [n for n in archive.namelist() if n.startswith('영문컬럼/')])
    shp = next((BASE / 'entrance-spatial').rglob('*.shp'))
    metadata = subprocess.check_output(['ogrinfo', '-al', '-so', str(shp)], text=True)
    assert 'ID["EPSG",4326]' in metadata
    exported = subprocess.check_output(['ogr2ogr', '--config', 'SHAPE_ENCODING', 'CP949', '-f', 'GeoJSON', '/vsistdout/', str(shp)], text=True)
    features = json.loads(exported)['features']
    fields = sorted(features[0]['properties'])
    assert not any(re.search(r'grade|slope|incline', key, flags=re.I) for key in fields)

    def counts(key):
        return dict(Counter(f['properties'].get(key) or 'unrecorded' for f in features))
    entrance.update({
        'catalog': 'https://data.seoul.go.kr/dataList/OA-21699/S/1/datasetView.do?tab=A',
        'catalog_license': '이용허락범위 제한 없음',
        'date_basis': counts('refDate'), 'shp_listing_date': '2023-01-02', 'dictionary_listing_date': '2023-04-21',
        'crs': 'EPSG:4326', 'records': len(features), 'unique_points': len({tuple(f['geometry']['coordinates']) for f in features}),
        'unique_facility_ids': len({f['properties']['sisulId'] for f in features}),
        'ramp_installation_codes': counts('ramp'), 'access_type_codes': counts('entrcHeigh'),
        'numeric_grade_field': False, 'fields': fields,
        'note': 'ED_EB description includes stairs with accessible ramp or vertical lift etc. (under 5 degrees); access type code only, no ramp grade value.',
        'dictionary': entrance_dictionary,
    })
    stats = checked(
        'seoul-sidewalk-stats-2025.xlsx', DATA_URL + '?infId=OA-22240&infSeq=1&seq=4&useCache=false',
        'f2e90f6f11625c17c7c9be0cdcc1b8299cc358f94561f24244d86c702efc01d6')
    book = load_workbook(BASE / stats['file'], read_only=True, data_only=True)
    detail = [row for row in book.worksheets[1].values if type(row[0]) is int]
    assert not any(isinstance(cell, str) and re.search('경사|기울기', cell)
                   for sheet in book for row in sheet.values for cell in row)
    stats.update({'catalog': 'https://data.seoul.go.kr/dataList/OA-22240/F/1/datasetView.do',
                  'listing_date': '2026-09-15', 'date_basis': '2025-12-31', 'sheets': book.sheetnames,
                  'detail_rows': len(detail), 'districts_in_manager_field': len({r[2] for r in detail if str(r[2]).endswith('구')}),
                  'slope_field': False, 'coordinates_or_crs': None})
    inv = checked('gnss-route-inventory.xlsx', GANGNAM_FILE,
                  '28fad03c52ad8ca43e1045280c172d76d3be9c7ca22052f4254b3477bb0751c0')
    rows = [r for r in load_workbook(BASE / inv['file'], read_only=True, data_only=True).worksheets[0].values if type(r[0]) is int]
    assert len(rows) == len({(r[4], r[5]) for r in rows}) == 608
    types = Counter()
    for row in rows:
        if row[1]:
            facility_kind = row[1].split('\n')[0]
        types[facility_kind] += 1
    inv.update({
        'notice': GANGNAM_NOTICE, 'theme': 'https://map.seoul.go.kr/smgis2/short/6OkfD',
        'theme_id': '1694517815685', 'launch_date': '2024-03-20', 'measurement_date_by_row': None,
        'redistribution_terms': 'separate inventory attachment re-use terms not verified',
        'actual_rows': len(rows), 'named_destination_count': len({r[5] for r in rows}),
        'degree_bands': dict(Counter(r[8] for r in rows)), 'facility_groups': dict(types),
        'numeric_slope_field': False, 'coordinates_or_crs_in_workbook': None,
    })
    return {'collected_kst': '2026-11-22', 'field_verified_by_donghaeng': False,
            'routing_eligible': False, 'entrance': entrance, 'sidewalk_statistics': stats, 'safe_route_inventory': inv}


if __name__ == '__main__':
    print(json.dumps(report(), ensure_ascii=False, indent=2))
