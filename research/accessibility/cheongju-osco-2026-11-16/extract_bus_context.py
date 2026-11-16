#!/usr/bin/env python3
"""Restore original OSM bus-relation members for research, without schedule claims."""
from pathlib import Path
import csv,gzip,hashlib,json
import osmium

ROOT=Path(__file__).resolve().parent
def packed(o):return {'id':o.id,'version':o.version,'timestamp':o.timestamp.isoformat(),'tags':dict(o.tags)}
def main():
    source=ROOT/'raw/geofabrik-korea-261115-pbf/response.bin'
    file=osmium.io.File(str(source),'pbf')
    data=json.loads(gzip.decompress((ROOT/'derived/osm-objects.json.gz').read_bytes()))
    routes=[r for r in data['relations'] if r['tags'].get('route')=='bus']
    want_ways={m['ref'] for r in routes for m in r['members'] if m['type']=='w'}
    want_nodes={m['ref'] for r in routes for m in r['members'] if m['type']=='n'}
    ways={w['id']:w for w in data['ways'] if w['id'] in want_ways}
    class Ways(osmium.SimpleHandler):
        def way(self,w):
            if w.id in want_ways and w.id not in ways:ways[w.id]={**packed(w),'nodes':[n.ref for n in w.nodes]}
    Ways().apply_file(file)
    want_nodes.update(n for w in ways.values() for n in w['nodes'])
    nodes={n['id']:n for n in data['nodes'] if n['id'] in want_nodes}
    print('bus member ways/nodes needed',len(want_ways),len(want_nodes),flush=True)
    class Nodes(osmium.SimpleHandler):
        def node(self,n):
            if n.id in want_nodes and n.id not in nodes:
                assert n.location.valid()
                nodes[n.id]={**packed(n),'coordinates':[n.location.lon,n.location.lat]}
    Nodes().apply_file(file)
    assert want_ways==set(ways) and want_nodes==set(nodes)
    for route in routes:
        route['regional_subset_members_complete']=route['members_complete']
        route['members_complete']=all((m['type']=='w' and m['ref'] in ways) or (m['type']=='n' and m['ref'] in nodes) for m in route['members'])
    features=[];rows=[]
    for route in routes:
        missing_relations=[m['ref'] for m in route['members'] if m['type']=='r']
        lines=[[nodes[n]['coordinates'] for n in ways[m['ref']]['nodes']] for m in route['members'] if m['type']=='w' and len(ways[m['ref']]['nodes'])>=2]
        features.append({'type':'Feature','id':'relation/'+str(route['id']),
            'geometry':{'type':'MultiLineString','coordinates':lines} if lines else None,
            'properties':{'osm_id':route['id'],'tags':route['tags'],'timestamp':route['timestamp'],
              'original_members':route['members'],'missing_nested_relations':missing_relations,
              'way_and_node_members_complete':True,'line_order_is_original_member_order':True,
              'gaps_not_joined':True,'current_timetable_verified':False,
              'low_floor_service_verified':False,'field_verified':False,'routing_eligible':False}})
        t=route['tags'];rows.append({'osm_relation_id':route['id'],**{k:t.get(k,'') for k in ['ref','name','from','to','operator','network','interval','opening_hours','wheelchair']},'osm_timestamp':route['timestamp'],'nested_relations_missing':len(missing_relations),'field_verified':False,'routing_eligible':False})
    out=ROOT/'derived/osm-bus-complete-context-v2.json.gz';assert not out.exists()
    raw=json.dumps({'metadata':data['source_metadata'],'relations':routes,'ways':list(ways.values()),'nodes':list(nodes.values())},ensure_ascii=False,separators=(',',':')).encode()
    with out.open('wb') as f:
        with gzip.GzipFile(fileobj=f,mode='wb',mtime=0) as z:z.write(raw)
    (ROOT/'derived/osm-bus-reference-lines.geojson').write_text(json.dumps({'type':'FeatureCollection','source_metadata':data['source_metadata'],'features':features},ensure_ascii=False,separators=(',',':'))+'\n')
    with (ROOT/'derived/osm-bus-relations.csv').open('w',newline='') as f:
        w=csv.DictWriter(f,fieldnames=list(rows[0]));w.writeheader();w.writerows(rows)
    summary={'pass':True,'bus_relations':len(routes),'way_members_restored':len(ways),'node_members_restored':len(nodes),
       'nested_relation_members_not_restored':sum(len(f['properties']['missing_nested_relations']) for f in features),
       'source_as_of':data['source_metadata']['source_as_of'],'refs':sorted(set(r['ref'] for r in rows if r['ref'])),
       'official_or_timetable_data':False,'field_verified':False,'routing_eligible':False,
       'topological_gaps_joined':0,'output_sha256':hashlib.sha256(out.read_bytes()).hexdigest(),
       'current_low_floor_operation_verified':False,'metadata_version':2,
       'current_payload':str(out.relative_to(ROOT)),
       'all_relation_members_complete':all(r['members_complete'] for r in routes)}
    (ROOT/'bus-context-results.json').write_text(json.dumps(summary,ensure_ascii=False,indent=2)+'\n')
    print(json.dumps(summary,ensure_ascii=False),flush=True)
if __name__=='__main__':main()
