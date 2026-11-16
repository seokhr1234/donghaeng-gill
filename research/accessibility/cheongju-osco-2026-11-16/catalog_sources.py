#!/usr/bin/env python3
"""Inventory preserved bytes; distinguish transport success, documents and datasets."""
from pathlib import Path
import collections,csv,hashlib,json,re,urllib.parse
from lxml import html

ROOT=Path(__file__).resolve().parent
MISMATCH={'osco-leaflet-page':'legacy board URL returned homepage','osco-parking-rates':'legacy board URL returned homepage','osco-firefloor-post':'unrelated event document, not the requested floor drawing'}
def provider(url):
    host=urllib.parse.urlsplit(url).hostname or ''
    if host in ['osco.or.kr','d2u77gqg41v474.cloudfront.net']:return 'official_venue_operator'
    if host.endswith('cbartgallery-osco.com'):return 'official_venue_gallery'
    if host.endswith('koddi.or.kr'):return 'official_bf_registry'
    if host.endswith('cjtgis.go.kr'):return 'official_municipal_gis'
    if host.endswith(('cheongju.go.kr','dcbis.go.kr','cjsisul.or.kr')):return 'official_municipal_service'
    if host.endswith('cjbus.co.kr'):return 'official_bus_committee'
    if host.endswith(('data.go.kr','localdata.go.kr','safekorea.go.kr','safetydata.go.kr','safemap.go.kr','ngii.go.kr')):return 'official_public_data_or_spatial_portal'
    if host.endswith('cbdc.co.kr'):return 'official_project_developer'
    if host.endswith('kric.go.kr'):return 'official_rail_data_portal'
    if host.endswith('visitkorea.or.kr'):return 'official_tourism'
    if host.endswith(('openstreetmap.org','geofabrik.de','overpass-api.de','overpass.kumi.systems')):return 'osm_source_or_distributor'
    if 'copernicus' in host or host=='registry.opendata.aws':return 'copernicus_product_or_distribution'
    if host.endswith(('statnorth.kr','python-choigosu.com','hiosong.kr')):return 'secondary_mirror_or_field_report'
    if host.endswith('essetel.com'):return 'regional_mobility_operator_site_affiliation_needs_confirmation'
    if host.endswith('haeahn.com'):return 'project_architect'
    return 'other'
def fmt(body,ident):
    if body.startswith(b'%PDF'):return 'PDF'
    if body.startswith(b'\x89PNG'):return 'PNG'
    if body.startswith(b'\xd0\xcf\x11\xe0'):return 'XLS/OLE'
    if body.startswith(b'PK\x03\x04'):return 'ZIP/HWPX'
    if body.startswith((b'II*\0',b'MM\0*')):return 'GeoTIFF'
    if ident.endswith('-pbf'):return 'OSM-PBF'
    text=body[:1000].lstrip().lower()
    if text.startswith((b'{',b'[')):return 'JSON'
    if b'<html' in text or b'<!doctype html' in text:return 'HTML'
    if b'<?xml' in text or b'<osm' in text:return 'XML'
    if 'csv' in ident:return 'CSV'
    return 'text/binary'
def main():
    sources=[];total=0;sha_checks=0
    for p in sorted((ROOT/'raw').glob('*/request.json')):
        req=json.loads(p.read_text());ident=req['id'];body_path=p.parent/'response.bin'
        body=body_path.read_bytes() if body_path.exists() else b''
        complete=req.get('transport_result')=='http_response' and body_path.exists()
        if complete:
            assert len(body)==req['bytes'] and hashlib.sha256(body).hexdigest()==req['sha256'];sha_checks+=1;total+=len(body)
        okay=complete and req.get('http_status')==200 and ident not in MISMATCH
        format=fmt(body,ident) if complete else None
        source={'id':ident,'provider_group':provider(req['url']),'url':req['url'],'method':req.get('method','POST' if req.get('form') is not None else 'GET'),
          'http_status':req.get('http_status'),'transport_result':req.get('transport_result'),'response_complete':complete,
          'requested_resource_verified':okay,'resource_validation_note':MISMATCH.get(ident),
          'bytes':req.get('bytes'),'sha256':req.get('sha256'),'format':format,
          'collected_at_utc':req.get('completed_at_utc'),'requested_at_kst':req['requested_at_kst'],
          'http_last_modified':req.get('response_headers',{}).get('last-modified'),
          'source_as_of':None,'page_modified_at':None,'declared_source_crs':None,'field_verified':False,
          'original_bytes_local_path':str(body_path.relative_to(ROOT)) if body_path.exists() else None,
          'request_record':str(p.relative_to(ROOT))}
        if okay and format=='HTML':
            try:
                doc=html.fromstring(body.decode('utf-8','replace'));title=doc.xpath('//title/text()');source['page_title']=title[0].strip() if title else None
                for s in doc.xpath('//script[@type="application/ld+json"]'):
                    try:j=json.loads(s.text or '')
                    except ValueError:continue
                    for entry in (j.get('@graph',[j]) if isinstance(j,dict) else []):
                        if entry.get('@type') in ['WebPage','Article'] and entry.get('dateModified'):source['page_modified_at']=entry['dateModified']
            except Exception:pass
        if ident=='geofabrik-korea-261115-pbf':source.update(source_as_of='2026-11-15T21:22:28Z',declared_source_crs='EPSG:4326',licence='ODbL-1.0')
        if ident=='osm-api-osco-live':source.update(declared_source_crs='EPSG:4326',licence='ODbL-1.0',source_as_of_note='No global timestamp claimed; per-object versions compared')
        if ident=='copernicus-n36e127':source.update(declared_source_crs='EPSG:4326; product vertical EGM2008',licence='Copernicus GLO-30-F; attribution and liability notice included',source_as_of_note='Individual tile acquisition date not established')
        if ident.startswith('cheongju-tgis-wfs-') and okay:
            try:
                j=json.loads(body)
                source.update(feature_count=len(j.get('features',[])),number_matched=j.get('numberMatched'),response_generated_at=j.get('timeStamp'),declared_source_crs=(j.get('crs') or {}).get('properties',{}).get('name'),licence='Reuse terms unconfirmed; research only')
            except ValueError:source['requested_resource_verified']=False
        if source['provider_group']=='secondary_mirror_or_field_report':source['primary_original_verified']=False;source['runtime_import_allowed']=False
        sources.append(source)
    (ROOT/'sources.json').write_text(json.dumps(sources,ensure_ascii=False,indent=2)+'\n')
    columns=['id','provider_group','url','method','http_status','transport_result','response_complete','requested_resource_verified','bytes','sha256','format','requested_at_kst','source_as_of','declared_source_crs','field_verified','resource_validation_note']
    with (ROOT/'sources.csv').open('w',encoding='utf-8-sig',newline='') as f:
        writer=csv.DictWriter(f,fieldnames=columns,extrasaction='ignore');writer.writeheader();writer.writerows(sources)
    summary={'requests':len(sources),'complete_response_hashes_verified':sha_checks,'complete_response_bytes':total,
      'http_status_counts':dict(collections.Counter(str(x['http_status']) for x in sources)),
      'transport_failed':sum(not x['response_complete'] for x in sources),'verified_http200_resources':sum(x['requested_resource_verified'] for x in sources),
      'http200_not_equal_to_dataset_acquired':True,'wrong_legacy_board_resources':MISMATCH,
      'provider_groups':dict(collections.Counter(x['provider_group'] for x in sources)),
      'collection_start_kst':min(x['requested_at_kst'] for x in sources),'collection_end_request_kst':max(x['requested_at_kst'] for x in sources),
      'web_search_extraction_evidence_not_original_bytes':True,'active_runtime_replaced':False,'new_slope_values_promoted':0,'field_verified':False}
    (ROOT/'collection-summary.json').write_text(json.dumps(summary,ensure_ascii=False,indent=2)+'\n')
    print(json.dumps(summary,ensure_ascii=False))
if __name__=='__main__':main()
