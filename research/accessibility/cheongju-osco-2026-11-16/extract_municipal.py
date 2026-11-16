#!/usr/bin/env python3
"""Preserve public municipal geometry in its own research dataset; do not activate it."""
from pathlib import Path
import collections,hashlib,json,re,urllib.parse,xml.etree.ElementTree as ET
from pyproj import CRS,Transformer
from shapely.geometry import shape,mapping,box
from shapely import force_2d, transform

ROOT=Path(__file__).resolve().parent
def digest(obj):
    normalized={**obj,'properties':dict(obj.get('properties',{}))}
    # The actual geometry is feature.geometry. GEOM serializes a Java byte-array
    # identity ([B@hex), which changes per response and carries no geometry value.
    if re.fullmatch(r'\[B@[0-9a-fA-F]+',str(normalized['properties'].get('GEOM',''))):normalized['properties'].pop('GEOM')
    return hashlib.sha256(json.dumps(normalized,ensure_ascii=False,sort_keys=True,separators=(',',':')).encode()).hexdigest()
def closed(g):
    if g['type']=='Polygon':return all(len(r)>=4 and r[0]==r[-1] for r in g['coordinates'])
    if g['type']=='MultiPolygon':return all(len(r)>=4 and r[0]==r[-1] for p in g['coordinates'] for r in p)
    return True
def main():
    out=ROOT/'municipal-derived';out.mkdir(exist_ok=True)
    grouped=collections.defaultdict(dict);sources=collections.defaultdict(list);failures=[];duplicates=0;conflicts=[];withheld=[]
    native_crs={};dates=collections.defaultdict(lambda:collections.defaultdict(list))
    for request in sorted((ROOT/'raw').glob('cheongju-tgis-wfs-*/request.json')):
        req=json.loads(request.read_text());params=urllib.parse.parse_qs(urllib.parse.urlsplit(req['url']).query)
        layer=params.get('typename',[''])[0].split(':')[-1];path=request.parent/'response.bin'
        if req.get('http_status')!=200 or not req.get('bytes') or not path.exists():
            reason=req.get('error')
            if path.exists():
                try:reason=' | '.join((x.text or '').strip() for x in ET.fromstring(path.read_bytes()).iter() if x.tag.rsplit('}',1)[-1] in ['ExceptionText','ServiceException']) or reason
                except ET.ParseError:pass
            failures.append({'source_id':req['id'],'layer':layer,'http_status':req.get('http_status'),'reason':reason,'treated_as_zero':False});continue
        try:data=json.loads(path.read_text())
        except ValueError:failures.append({'source_id':req['id'],'layer':layer,'reason':'not JSON','treated_as_zero':False});continue
        if data.get('type')!='FeatureCollection':failures.append({'source_id':req['id'],'layer':layer,'reason':'not a FeatureCollection','treated_as_zero':False});continue
        features=data.get('features',[]);matched=data.get('numberMatched',data.get('totalFeatures'))
        crs_name=(data.get('crs') or {}).get('properties',{}).get('name')
        if features:assert crs_name, 'Do not infer nonempty source CRS from coordinate magnitude'
        source_crs=CRS.from_user_input(crs_name or 'EPSG:5186')
        native_crs[layer]=source_crs.to_string()
        sources[layer].append({'source_id':req['id'],'source_sha256':req['sha256'],'features_returned':len(features),'number_matched':matched,'query_complete':matched==len(features),'response_generated_at':data.get('timeStamp'),'response_crs':crs_name,'query_bbox':params.get('bbox',[None])[0]})
        forward=Transformer.from_crs(source_crs,4326,always_xy=True)
        reverse=Transformer.from_crs(4326,source_crs,always_xy=True)
        for f in features:
            ident=f['id'];fingerprint=digest(f)
            if ident in grouped[layer]:
                duplicates+=1
                if grouped[layer][ident]['source_fingerprint']!=fingerprint:conflicts.append({'layer':layer,'id':ident,'source_id':req['id']})
                else:grouped[layer][ident]['properties']['source_ids'].append(req['id'])
                continue
            if not f.get('geometry') or not closed(f['geometry']):withheld.append({'id':ident,'layer':layer,'source_id':req['id'],'reason':'missing geometry or unclosed original ring'});continue
            original=shape(f['geometry'])
            if not original.is_valid:withheld.append({'id':ident,'layer':layer,'source_id':req['id'],'reason':'invalid original geometry; not repaired'});continue
            original=force_2d(original);geographic=transform(original,forward.transform,interleaved=False)
            assert geographic.is_valid
            roundtrip=transform(geographic,reverse.transform,interleaved=False)
            assert original.hausdorff_distance(roundtrip)<.01, 'Projection round-trip exceeds 1cm computational tolerance'
            # This checks numeric transformation only, never positional/survey accuracy.
            assert geographic.intersects(box(127.27,36.58,127.40,36.68)), 'Unexpected map axis order or geography'
            props=f.get('properties',{})
            for key in ['REG_YMD','UPT_YMD','ESB_YMD']:
                if props.get(key) not in [None,'']:dates[layer][key].append(str(props[key]))
            selected={k:v for k,v in props.items() if k in ['MGRNU','MAPCODE','GEOMSEQ','CRS_TYPE','DONG_NAM','RI_NAM','CSS_NAM','REG_YMD','UPT_YMD','ESB_YMD','HOL','VEL','EVE','AREA','LEN','LENGTH','SHAPE_AREA','SHAPE_LEN']}
            grouped[layer][ident]={'type':'Feature','id':ident,'geometry':mapping(geographic),'source_fingerprint':fingerprint,
              'properties':{'layer':layer,'original_source_crs':source_crs.to_string(),'raw_registered_fields':selected,'source_ids':[req['id']],
                'source_as_of':None,'field_verified':False,'routing_eligible':False,'license_status':'unconfirmed; private research only','z_not_used_as_ground_elevation':True}}
    assert not conflicts, 'Changed municipal objects across requests require explicit version review'
    names=json.loads((ROOT/'municipal-public-layer-definitions.json').read_text())['layers'];names={x['id']:x['name'] for x in names}
    layers=[]
    for layer,items in sorted(sources.items()):
        features=list(grouped[layer].values())
        for f in features:f.pop('source_fingerprint')
        meta={'provider':'청주시 교통지리정보시스템 (public anonymous map read)','layer':layer,'layer_name':names.get(layer),'source_crs':native_crs[layer],
          'derived_crs':'EPSG:4326','source_as_of':None,'mapping_scale':None,'source_positional_accuracy_m':None,'vertical_datum':None,
          'source_ids':[s['source_id'] for s in items],'field_verified':False,'routing_eligible':False,'license_status':'unconfirmed; private research only',
          'notice':'Registered geometry, not certified sidewalk centerlines, current passability or a 1:1000 survey claim; dates are raw database fields.'}
        file=out/(layer+'.geojson');file.write_text(json.dumps({'type':'FeatureCollection','source_metadata':meta,'features':features},ensure_ascii=False,separators=(',',':'))+'\n')
        layer_dates={k:{'nonempty_values':len(v),'earliest_raw':min(v),'latest_raw':max(v),'meaning':'registration/update/installation field; not asserted to be survey date'} for k,v in dates[layer].items() if v}
        layers.append({'layer':layer,'name':names.get(layer),'unique_geometries':len(features),'source_crs':native_crs[layer],'derived_crs':'EPSG:4326','sources':items,'geometry_types':dict(collections.Counter(f['geometry']['type'] for f in features)),'raw_date_fields':layer_dates,'file':str(file.relative_to(ROOT)),'sha256':hashlib.sha256(file.read_bytes()).hexdigest(),'physical_absence_inferred_from_zero':False})
    result={'pass':True,'layers':layers,'unique_geometries':sum(x['unique_geometries'] for x in layers),'duplicate_features_deduplicated_by_exact_id_and_content':duplicates,
      'changed_source_conflicts':conflicts,'withheld_invalid_geometries':withheld,'failed_requests':failures,
      'withheld_invalid_unique_count':len({(x['layer'],x['id']) for x in withheld}),
      'withheld_invalid_observation_count':len(withheld),
      'ignored_transient_field':'GEOM only when exactly a Java byte-array identity [B@hex; original geometry and other attributes still compared; raw responses preserved',
      'source_rings_closed_without_repair':True,'projection_roundtrip_tolerance_m':.01,'projection_check_is_survey_accuracy':False,
      'z_promoted_to_ground_elevation':False,'active_runtime_replaced':False,'field_verified':False,'routing_eligible':False,'redistribution_terms_verified':False}
    (ROOT/'municipal-geometry-results.json').write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n')
    print(json.dumps({'layers':len(layers),'unique_geometries':result['unique_geometries'],'withheld_invalid':len(withheld),'failed_requests':len(failures),'counts':{x['name']:x['unique_geometries'] for x in layers}},ensure_ascii=False))
if __name__=='__main__':main()
