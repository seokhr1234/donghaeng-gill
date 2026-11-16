#!/usr/bin/env python3
"""Extract a complete-node regional OSM research subset; never activate routing."""
from pathlib import Path
import collections, gzip, hashlib, json, math
import osmium

ROOT = Path(__file__).resolve().parent
RAW = ROOT / 'raw/geofabrik-korea-261115-pbf/response.bin'
OUT = ROOT / 'derived'
BBOX = [127.28, 36.59, 127.39, 36.67]
CENTER = (36.6267203, 127.335363)

def packed(obj):
    return {'id': obj.id, 'version': obj.version, 'timestamp': obj.timestamp.isoformat(),
            'tags': dict(obj.tags)}

def distance(x, y):
    a,b = map(math.radians, CENTER)
    c,d = math.radians(y), math.radians(x)
    q = math.sin((c-a)/2)**2 + math.cos(a)*math.cos(c)*math.sin((d-b)/2)**2
    return 12742000 * math.asin(min(1, math.sqrt(q)))

def dump(name, value, compressed=False):
    raw = (json.dumps(value, ensure_ascii=False, separators=(',', ':'), allow_nan=False)+'\n').encode()
    target = OUT / name
    if compressed:
        with target.open('wb') as f:
            with gzip.GzipFile(fileobj=f, mode='wb', mtime=0) as z:z.write(raw)
    else:target.write_bytes(raw)
    return {'path':str(target.relative_to(ROOT)), 'bytes':target.stat().st_size,
            'sha256':hashlib.sha256(target.read_bytes()).hexdigest()}

def run():
    OUT.mkdir(exist_ok=True)
    assert not (OUT/'osm-objects.json.gz').exists(), 'Preserve existing extraction'
    expected = (ROOT/'raw/geofabrik-korea-261115-md5/response.bin').read_text().split()[0]
    assert hashlib.md5(RAW.read_bytes()).hexdigest()==expected
    file = osmium.io.File(str(RAW), 'pbf')
    with osmium.io.Reader(file) as reader:source_as_of=reader.header().get('osmosis_replication_timestamp')
    request=json.loads((RAW.parent/'request.json').read_text())
    nodes, ways, relations = {}, {}, {}
    class Nodes(osmium.SimpleHandler):
        def node(self, n):
            if n.location.valid() and BBOX[0]<=n.location.lon<=BBOX[2] and BBOX[1]<=n.location.lat<=BBOX[3]:
                nodes[n.id]={**packed(n), 'coordinates':[n.location.lon,n.location.lat]}
    Nodes().apply_file(file)
    inside=set(nodes)
    print('bbox nodes',len(nodes),flush=True)
    missing=set()
    class Ways(osmium.SimpleHandler):
        def way(self,w):
            refs=[n.ref for n in w.nodes]
            if any(n in inside for n in refs):
                ways[w.id]={**packed(w),'nodes':refs}
                missing.update(n for n in refs if n not in nodes)
        def relation(self,r):
            if any((m.type=='w' and m.ref in ways) or (m.type=='n' and m.ref in inside) for m in r.members):
                relations[r.id]={**packed(r),'members':[{'type':m.type,'ref':m.ref,'role':m.role} for m in r.members]}
    Ways().apply_file(file)
    print('ways/relations/context nodes needed',len(ways),len(relations),len(missing),flush=True)
    class Context(osmium.SimpleHandler):
        def node(self,n):
            if n.id in missing:
                assert n.location.valid()
                nodes[n.id]={**packed(n),'coordinates':[n.location.lon,n.location.lat],'outside_bbox_context':True}
    if missing:Context().apply_file(file)
    assert all(n in nodes for w in ways.values() for n in w['nodes'])
    for r in relations.values():
        r['members_complete']=all((m['type']=='n' and m['ref'] in nodes) or (m['type']=='w' and m['ref'] in ways) for m in r['members'])
    metadata={'source_id':'geofabrik-korea-261115-pbf','source_url':request['url'],
       'source_as_of':source_as_of,'collected_at_utc':request['completed_at_utc'],
       'source_crs':'EPSG:4326','vertical_datum':None,'license':'ODbL-1.0',
       'attribution':'© OpenStreetMap contributors','field_verified':False,
       'routing_eligible':False,'active_runtime_replaced':False,'new_slope_values_promoted':0,
       'scope':'Ways with at least one source node in research bbox; complete way node references restored; not an administrative completeness claim',
       'relation_notice':'Relations retained with all raw member IDs; missing remote members explicitly marked, not reconstructed'}
    objects={'schema':'osco-osm-research-v1','bbox':BBOX,'source_metadata':metadata,
             'nodes':list(nodes.values()),'ways':list(ways.values()),'relations':list(relations.values())}
    assets=[dump('osm-objects.json.gz',objects,True)]
    layers=collections.defaultdict(list)
    tag_counts=collections.Counter();highways=collections.Counter();facility_counts=collections.Counter()
    bands={str(v):collections.Counter() for v in [1000,2000,5000]}
    access_keys=['wheelchair','width','incline','surface','smoothness','kerb','kerb:height','tactile_paving','lit','sidewalk','foot','access','crossing','barrier','opening_hours','ele']
    def feature(kind,obj,geometry):
        tags=obj['tags']
        return {'type':'Feature','id':kind+'/'+str(obj['id']),'geometry':geometry,
                'properties':{'osm_type':kind,'osm_id':obj['id'],'version':obj['version'],
                 'osm_timestamp':obj['timestamp'],'tags':tags,'field_verified':False,'routing_eligible':False}}
    def classify(kind,obj,geom):
        tags=obj['tags'];f=feature(kind,obj,geom)
        if 'highway' in tags and kind=='way':layers['roads'].append(f);highways[tags['highway']]+=1
        if 'building' in tags or 'building:part' in tags:layers['buildings'].append(f)
        if ('public_transport' in tags or tags.get('highway')=='bus_stop' or 'railway' in tags):layers['transport'].append(f)
        if any(k in tags for k in ['barrier','crossing','kerb','tactile_paving','entrance']) or tags.get('highway') in ['crossing','elevator','steps']:
            layers['access_points'].append(f)
        if any(k in tags for k in ['amenity','shop','tourism','healthcare','emergency']) or tags.get('leisure') in ['park','playground','garden']:
            layers['facilities'].append(f)
            key=tags.get('amenity',tags.get('healthcare',tags.get('emergency',tags.get('shop',tags.get('tourism',tags.get('leisure'))))))
            facility_counts[key]+=1
        if any(k in tags for k in ['waterway','water','natural','landuse','leisure']):layers['land_water_green'].append(f)
        for k in access_keys:
            if k in tags:tag_counts[k]+=1
        if kind=='node':
            x,y=obj['coordinates'];d=distance(x,y)
            category=tags.get('amenity') or ('bus_stop' if tags.get('highway')=='bus_stop' else None)
            if category:
                for limit,c in bands.items():
                    if d<=int(limit):c[category]+=1
    for n in nodes.values():
        if n['id'] in inside and n['tags']:classify('node',n,{'type':'Point','coordinates':n['coordinates']})
    for w in ways.values():
        coords=[nodes[n]['coordinates'] for n in w['nodes']]
        if len(coords)<2:continue
        polygon=len(coords)>=4 and w['nodes'][0]==w['nodes'][-1] and (any(k in w['tags'] for k in ['building','building:part','landuse','leisure','amenity']) or w['tags'].get('area')=='yes')
        classify('way',w,{'type':'Polygon','coordinates':[coords]} if polygon else {'type':'LineString','coordinates':coords})
    for name,features in layers.items():assets.append(dump('osm-'+name+'.geojson',{'type':'FeatureCollection','source_metadata':metadata,'features':features}))
    # Shared-node topology is a registration audit only, not pedestrian permission.
    parent={};edge_count=0
    def find(x):
        parent.setdefault(x,x)
        while parent[x]!=x:parent[x]=parent[parent[x]];x=parent[x]
        return x
    for w in ways.values():
        if 'highway' not in w['tags']:continue
        for a,b in zip(w['nodes'],w['nodes'][1:]):
            if a==b:continue
            parent[find(a)]=find(b);edge_count+=1
    components=collections.Counter(find(n) for n in parent)
    named=[{'type':'node','id':n['id'],'tags':n['tags'],'coordinates':n['coordinates'],'distance_m':round(distance(*n['coordinates']),1)} for n in nodes.values() if n['id'] in inside and any(s in n['tags'].get('name','').lower() for s in ['오스코','osco','오송역'])]
    named += [{'type':'way','id':w['id'],'tags':w['tags'],'geometry_in':'osm-objects.json.gz'} for w in ways.values() if any(s in w['tags'].get('name','').lower() for s in ['오스코','osco','오송역'])]
    summary={'pass':True,'bbox':BBOX,'source_metadata':metadata,'source_pbf_bytes':RAW.stat().st_size,
      'source_pbf_sha256':request['sha256'],'source_pbf_md5_verified':True,
      'bbox_nodes':len(inside),'context_nodes':len(nodes)-len(inside),'ways':len(ways),'relations':len(relations),
      'incomplete_context_relations':sum(not r['members_complete'] for r in relations.values()),
      'all_way_node_refs_restored':True,'layers':{k:len(v) for k,v in layers.items()},
      'highway_counts':dict(highways),'access_tag_object_counts':dict(tag_counts),'facility_object_counts':dict(facility_counts),
      'point_facilities_within_meters':{k:dict(v) for k,v in bands.items()},
      'registered_highway_topology':{'segments':edge_count,'nodes':len(parent),'components':len(components),'largest_components':components.most_common(10),'pedestrian_eligibility_checked':False,'coordinate_snapping':0},
      'named_venue_and_station_objects':named,'assets':assets}
    (ROOT/'osm-extraction-results.json').write_text(json.dumps(summary,ensure_ascii=False,indent=2)+'\n')
    print(json.dumps({k:summary[k] for k in ['bbox_nodes','context_nodes','ways','relations','layers','access_tag_object_counts']},ensure_ascii=False),flush=True)

if __name__=='__main__':run()
