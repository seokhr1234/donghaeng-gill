#!/usr/bin/env python3
"""Check saved geometries against source objects and independently fetched OSM XML."""
from pathlib import Path
import collections, gzip, hashlib, json, xml.etree.ElementTree as ET

ROOT=Path(__file__).resolve().parent

def main():
    data=json.loads(gzip.decompress((ROOT/'derived/osm-objects.json.gz').read_bytes()))
    objects={}
    for kind,key in [('node','nodes'),('way','ways'),('relation','relations')]:
        for obj in data[key]:
            ident=kind+'/'+str(obj['id']);assert ident not in objects
            objects[ident]=obj
    nodes={n['id']:n for n in data['nodes']}
    checks=[]
    for path in sorted((ROOT/'derived').glob('osm-*.geojson')):
        fc=json.loads(path.read_text());ids=set()
        assert fc['source_metadata']['field_verified'] is False
        assert fc['source_metadata']['routing_eligible'] is False
        for f in fc['features']:
            assert f['id'] not in ids;ids.add(f['id'])
            obj=objects[f['id']]
            assert f['properties']['tags']==obj['tags']
            assert f['properties']['osm_timestamp']==obj['timestamp']
            if f['geometry']['type']=='Point':expected=obj['coordinates']
            else:
                expected=[nodes[n]['coordinates'] for n in obj['nodes']]
                if f['geometry']['type']=='Polygon':expected=[expected]
            assert f['geometry']['coordinates']==expected
            assert f['properties']['field_verified'] is False and f['properties']['routing_eligible'] is False
        checks.append({'file':path.name,'features':len(ids),'source_geometry_and_tags_match':True})
    live={}
    xml=ET.parse(ROOT/'raw/osm-api-osco-live/response.bin').getroot()
    for x in xml:
        if x.tag not in ['node','way','relation']:continue
        o={'id':int(x.attrib['id']),'version':int(x.attrib['version']),
           'tags':{t.attrib['k']:t.attrib['v'] for t in x.findall('tag')}}
        if x.tag=='node':o['coordinates']=[float(x.attrib['lon']),float(x.attrib['lat'])]
        elif x.tag=='way':o['nodes']=[int(n.attrib['ref']) for n in x.findall('nd')]
        elif x.tag=='relation':o['members']=[{'type':{'node':'n','way':'w','relation':'r'}[m.attrib['type']],'ref':int(m.attrib['ref']),'role':m.attrib['role']} for m in x.findall('member')]
        live[x.tag+'/'+str(o['id'])]=o
    common=set(live)&set(objects)
    different_version=[];same_version_mismatch=[];same_version=0
    for ident in sorted(common):
        a,b=objects[ident],live[ident]
        if a['version']!=b['version']:
            different_version.append({'id':ident,'pbf_version':a['version'],'live_version':b['version']});continue
        same_version+=1
        if any(a.get(k)!=b.get(k) for k in ['tags','coordinates','nodes','members']):same_version_mismatch.append(ident)
    assert not same_version_mismatch, 'Independent live source disagrees at identical OSM version'
    # Missing objects outside the common map scope are not interpreted as deletions.
    request=json.loads((ROOT/'raw/osm-api-osco-live/request.json').read_text())
    summary={'pass':True,'source_objects':len(objects),'duplicate_source_ids':0,
       'all_way_node_references_present':all(n in nodes for w in data['ways'] for n in w['nodes']),
       'geometry_checks':checks,'independent_live_api':{'url':request['url'],'collected_at_utc':request['completed_at_utc'],
       'source_as_of':None,'note':'Live database response has per-object timestamps; no global snapshot time is claimed',
       'objects':len(live),'common_objects':len(common),'same_version_objects':same_version,
       'same_version_content_mismatches':same_version_mismatch,'changed_versions':different_version,
       'unmatched_objects_treated_as_deletions':False},'active_runtime_replaced':False,'new_slope_values_promoted':0,'field_verified':False}
    (ROOT/'osm-independent-validation.json').write_text(json.dumps(summary,ensure_ascii=False,indent=2)+'\n')
    print(json.dumps({'pass':True,'features_checked':sum(x['features'] for x in checks),'live_common':len(common),'same_version':same_version,'changed_version_count':len(different_version),'same_version_mismatches':len(same_version_mismatch)},ensure_ascii=False))

if __name__=='__main__':main()
