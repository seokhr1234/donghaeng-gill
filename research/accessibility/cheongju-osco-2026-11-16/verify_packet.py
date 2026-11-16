#!/usr/bin/env python3
"""Verify research packet bindings; this is not a field-accessibility test."""
from pathlib import Path
import gzip,hashlib,json,subprocess
from lxml import html
import xlrd
from pyproj import Transformer
from shapely.geometry import shape
from shapely import transform

ROOT=Path(__file__).resolve().parent
REPO=ROOT.parents[2]
BASE='bea574660cb8107c19dafd12c9d865cb8582c46a'
def read(name):return json.loads((ROOT/name).read_text())
def sha(path):return hashlib.sha256(path.read_bytes()).hexdigest()
def main():
    sources=read('sources.json');by_id={x['id']:x for x in sources};assert len(by_id)==len(sources)
    for s in sources:
        assert s['field_verified'] is False
        if s['response_complete']:
            p=ROOT/s['original_bytes_local_path'];assert p.exists() and p.stat().st_size==s['bytes']
    facts=read('primary-evidence.json');bf=facts['bf_certificate']
    workbook=xlrd.open_workbook(file_contents=(ROOT/'raw/bf-osco-excel/response.bin').read_bytes())
    rows=[workbook.sheet_by_index(0).row_values(i) for i in range(workbook.sheet_by_index(0).nrows)]
    main=next(row for row in rows if len(row)>1 and row[1]==bf['certificate_number'])
    assert [main[i] for i in [2,3,11,12]]==[bf['kind'],bf['grade'],bf['issued'],bf['reported_expiry']]
    text=html.fromstring((ROOT/'raw/bf-osco-detail-main/response.bin').read_bytes().decode('utf-8')).text_content()
    assert all(s in text for s in [bf['certificate_number']+'호',bf['grade'],bf['issued'],bf['reported_expiry']])
    assert sum(facts['parking_claims']['operator_plan_breakdown'].values())==991
    assert '1,114' in (ROOT/'raw/osco-facility-pdf/extracted.txt').read_text()
    osm=read('osm-extraction-results.json')
    for asset in osm['assets']:assert sha(ROOT/asset['path'])==asset['sha256']
    assert read('osm-independent-validation.json')['pass'] is True
    assert read('dem-validation.json')['pass'] is True
    bus=read('bus-context-results.json');payload=json.loads(gzip.decompress((ROOT/bus['current_payload']).read_bytes()))
    assert sha(ROOT/bus['current_payload'])==bus['output_sha256']
    way_ids={x['id'] for x in payload['ways']};node_ids={x['id'] for x in payload['nodes']}
    assert all(n in node_ids for w in payload['ways'] for n in w['nodes'])
    assert all(r['members_complete'] and all((m['type']=='w' and m['ref'] in way_ids) or (m['type']=='n' and m['ref'] in node_ids) for m in r['members']) for r in payload['relations'])
    city=read('municipal-geometry-results.json');count=0;raw_cache={};valid_ids=set()
    back=Transformer.from_crs(4326,5186,always_xy=True)
    for layer in city['layers']:
        path=ROOT/layer['file'];assert sha(path)==layer['sha256']
        fc=json.loads(path.read_text());assert fc['source_metadata']['routing_eligible'] is False
        for f in fc['features']:
            assert f['properties']['field_verified'] is False and f['properties']['routing_eligible'] is False
            ident=(layer['layer'],f['id']);assert ident not in valid_ids;valid_ids.add(ident)
            source=f['properties']['source_ids'][0]
            if source not in raw_cache:raw_cache[source]={x['id']:x for x in json.loads((ROOT/'raw'/source/'response.bin').read_text())['features']}
            native=shape(raw_cache[source][f['id']]['geometry']);saved=shape(f['geometry'])
            assert saved.is_valid and native.is_valid
            assert native.hausdorff_distance(transform(saved,back.transform,interleaved=False))<.01
            count+=1
    assert count==city['unique_geometries']==5462
    assert not valid_ids&{(x['layer'],x['id']) for x in city['withheld_invalid_geometries']}
    assert read('osm-municipal-position-review.json')['identity_automatically_merged']==0
    assert read('secondary-facilities-review.json')['raw_official_dataset_verified'] is False
    changes=subprocess.check_output(['git','diff','--name-only',BASE],cwd=REPO,text=True).splitlines()
    allowed=lambda x:x in ['README.md','수정이력.md'] or x.startswith('research/accessibility/cheongju-osco-2026-11-16/')
    assert all(allowed(x) for x in changes),'App or earlier research changed'
    artifacts=[]
    for folder in ['derived','municipal-derived','previews']:
        for p in sorted((ROOT/folder).glob('*')):
            if p.is_file():artifacts.append({'file':str(p.relative_to(ROOT)),'bytes':p.stat().st_size,'sha256':sha(p),'distribution_status':'private_research_hold' if folder=='municipal-derived' else 'attribution_and_licence_required'})
    report={'pass':True,'raw_complete_response_files_present':sum(s['response_complete'] for s in sources),
      'raw_byte_hashes_verified_by':'collection-summary.json / catalog_sources.py',
      'official_bf_html_excel_claims_match':True,'source_geometry_asset_hashes_match':True,
      'bus_relation_members_complete':True,'saved_municipal_geometry_count_checked':count,
      'projection_numeric_tolerance_m':.01,'numeric_tolerance_is_field_accuracy':False,
      'invalid_original_geometries_not_silently_repaired':True,'source_code_and_prior_research_preserved':True,
      'base_commit':BASE,'field_verified':False,'new_slope_values_promoted':0,
      'app_runtime_changed':False,'vercel_deployed':False,'apk_rebuilt':False,'new_paid_provider_calls':0,
      'artifacts':artifacts}
    (ROOT/'packet-verification.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n')
    print(json.dumps({k:v for k,v in report.items() if k!='artifacts'},ensure_ascii=False))
if __name__=='__main__':main()
