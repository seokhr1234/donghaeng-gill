"""Extract slope-coded public Smart Seoul Map route sections. Providers' reuse terms remain unconfirmed."""
from collections import Counter
import gzip
import hashlib
import json
import re
from pathlib import Path

from shapely import LineString, STRtree
from shapely.geometry import shape

HERE = Path(__file__).resolve().parent
INPUT = HERE / 'gnss-theme-captured.json'
OUT = HERE / 'gnss-sloped-route-lines.geojson.gz'
REPORT = HERE / 'gnss-route-layer-audit.json'
BOUNDARY = Path('/workspace/donghaeng-current-check-20261115/research/accessibility/seoul-rest-2026-11-20/derived/osm-boundaries.geojson')
THEME = '1694517815685'
VIEWER = 'https://map.seoul.go.kr/smgis2/short/6OkfD'
COLORS = {'#00FF00': ('하', '초록색'), '#FFCC00': ('중', '노란색'),
          '#FF6600': ('중상', '주황색'), '#FF0000': ('상', '빨간색')}
def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def run():
    dump = json.loads(INPUT.read_bytes())[THEME]
    types = Counter()
    output = []
    counts = Counter()
    ids = set()
    canonical = set()
    by_profile_color = {}
    bound = [180, 90, -180, -90]
    mids = []
    for item in dump['features']:
        p = item['properties']
        g = p['cot_coord_data']
        types[g['type']] += 1
        if g['type'] != 'LineString' or p.get('cot_name_02') != '보행 경로의 앞,뒤 경사 난이도':
            continue
        fid = p['cot_conts_id']
        assert fid not in ids
        ids.add(fid)
        coords = tuple(map(tuple, g['coordinates']))
        assert all(len(c)==2 and 126.7<c[0]<127.3 and 37.35<c[1]<37.8 for c in coords)
        line = LineString(coords)
        assert line.is_valid and line.length>0
        mids.append(line.interpolate(.5, normalized=True))
        canonical.add(min(coords,coords[::-1]))
        w,s,e,n = line.bounds
        bound = [min(bound[0],w), min(bound[1],s), max(bound[2],e), max(bound[3],n)]
        color = p['cot_line_color']
        difficulty, korean_color = COLORS[color]
        legend = p['cot_value_02']
        band = re.search(rf'{korean_color} \((\d+)[˚°]?(?:~(\d+)[˚°]|[˚°]이상)\)', legend)
        assert band, (color,legend)
        start = int(band[1])
        end = int(band[2]) if band[2] else None
        profile = p['sub_cate_name']
        k = (profile,color)
        old = by_profile_color.setdefault(k,{'difficulty':difficulty,'lower_deg':start,'upper_deg':end})
        assert old == {'difficulty':difficulty,'lower_deg':start,'upper_deg':end}
        counts[k]+=1
        output.append({
            'type':'Feature','id':fid,'geometry':g,'properties':{
                'source_theme_id':THEME,'source_content_id':fid,
                'mobility_profile':profile,'source_district_code':p['sgg_cd'],
                'source_length_raw':p['cot_value_01'],'source_length_m':float(p['cot_value_01']),
                'source_band_color':color,'source_slope_label':p['cot_name_02'],
                'source_profile_legend_ko':legend,'difficulty':difficulty,
                'published_band_lower_deg':start,'published_band_upper_deg':end,
                'observed_slope_deg':None,'observed_slope_percent':None,'point_or_segment_measurement_date':None,
                'field_verified_by_donghaeng':False,'routing_eligible':False,
            }
        })
    all_districts = json.loads(BOUNDARY.read_bytes())['features']
    district_data = [(f['properties']['name'],shape(f['geometry'])) for f in all_districts
                     if f['properties']['name']!='서울특별시']
    districts, district_shapes = zip(*district_data)
    assert len(districts) == 25
    boundary_tree = STRtree(district_shapes)
    spatial = Counter()
    for midpoint in mids:
        for idx in boundary_tree.query(midpoint, predicate='within'):
            spatial[districts[idx]]+=1
    bands = {k:{**by_profile_color[(p,c)],'records':counts[(p,c)],'color':c}
             for p,c in counts for k in [p + ' / ' + COLORS[c][0]]}
    meta = {
       'source_theme_id':THEME,'source_viewer':VIEWER,
       'source_provider':'서울특별시 스마트서울맵 · 보행약자 안전 이동경로',
       'theme_metadata_last_update':'2025-03-17T09:30:48+09:00',
       'retrieved_date_kst':'2026-11-22','published_crs_label':None,
       'geometry_format':'GeoJSON nested cot_coord_data LineString in WGS84-style lon/lat. Source payload has no CRS declaration.',
       'dataset_measurement_dates':None,
       'rights_status':'Local research only. Source API and dataset redistribution terms not verified.',
       'field_verified_by_donghaeng':False,'routing_eligible':False,
    }
    raw = (json.dumps({'type':'FeatureCollection','metadata':meta,'features':output},ensure_ascii=False,
                      separators=(',',':'))+'\n').encode()
    OUT.write_bytes(gzip.compress(raw,compresslevel=6,mtime=0))
    assert gzip.decompress(OUT.read_bytes()) == raw
    result = {**meta,'viewer_http_status':200,
      'direct_response_body_retrieval':'Browser received HTTP 200. Saved theme object after its public client parsed the response. Saved SHA is of the browser object, not raw HTTP bytes.',
      'captured_browser_object':{'file':INPUT.name,'bytes':INPUT.stat().st_size,'sha256':digest(INPUT)},
      'output_local_only':{'file':OUT.name,'bytes':OUT.stat().st_size,'sha256':digest(OUT)},
      'viewer_top_level_feature_count':len(dump['features']),'nested_geometry_types':dict(types),
      'normalized_slope_class_records':len(output),'valid_class_records':len(ids),
      'exact_geometry_distinct_ignoring_orientation':len(canonical),
      'stated_district_code_count':len({f['properties']['source_district_code'] for f in output}),
      'matched_districts_by_line_midpoint':len(spatial),'district_counts_by_midpoint':dict(sorted(spatial.items())),
      'not_matched_by_midpoint':len(output)-sum(spatial.values()),
      'district_join_reference_sha256':digest(BOUNDARY),
      'slope_class_by_profile_and_color':bands,'bounds_lon_lat':bound,
      'mapping':'Published style color identifies a category according to that mobility profile legend. Cross-profile duplicated lines are retained; no midpoint or exact slope is estimated. Raw route section orientation is retained; payload does not provide separate signed ascent and descent values.',
    }
    REPORT.write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n')
    print(json.dumps({k:result[k] for k in ('normalized_slope_class_records','matched_districts_by_line_midpoint','not_matched_by_midpoint','output_local_only')},ensure_ascii=False))


if __name__=='__main__':
    run()
