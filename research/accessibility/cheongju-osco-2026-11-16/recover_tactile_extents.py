#!/usr/bin/env python3
"""Recover readable public map extents; preserve invalid-source coverage gaps."""
from pathlib import Path
import concurrent.futures,json,urllib.parse
from pyproj import Transformer
import collect
ROOT=Path(__file__).resolve().parent

def main():
    target=ROOT/'tactile-recovery-results.json';assert not target.exists()
    project=Transformer.from_crs(4326,5186,always_xy=True)
    pending=[([127.335,36.63,127.39,36.67],'ne')];leaves=[];records=[]
    for depth in range(1,4):
        plan=[]
        for box,parent in pending:
            x0,y0,x1,y1=box;xm,ym=(x0+x1)/2,(y0+y1)/2
            for i,b in enumerate([[x0,y0,xm,ym],[xm,y0,x1,ym],[x0,ym,xm,y1],[xm,ym,x1,y1]]):
                bounds=project.transform_bounds(*b,densify_pts=21)
                params={'request':'GetFeature','version':'1.1.1','typename':'tgis:GT_C094_A','outputFormat':'application/json','bbox':','.join(map(str,bounds))+',EPSG:5186','maxFeatures':2000}
                plan.append({'id':'cheongju-tgis-wfs-tactile-'+parent+'-d'+str(depth)+'-'+str(i),'url':'https://www.cjtgis.go.kr/map/proxy/wfs.do?'+urllib.parse.urlencode(params),'layer':'GT_C094_A','research_bbox_lonlat':b,'timeout':45,'retry_reason':'Smaller normal public map viewport after invalid source LinearRing; source geometry is never repaired'})
        if not plan:break
        (ROOT/('plans/19-tactile-recovery-depth'+str(depth)+'.json')).write_text(json.dumps(plan,ensure_ascii=False,indent=2)+'\n')
        with concurrent.futures.ThreadPoolExecutor(max_workers=2) as pool:responses=list(pool.map(collect.collect,plan))
        pending=[]
        for req in responses:
            body=(ROOT/req['response_path']).read_bytes() if req.get('response_path') else b''
            good=False
            if req.get('http_status')==200:
                try:
                    j=json.loads(body);good=j.get('type')=='FeatureCollection' and len(j.get('features',[]))==j.get('numberMatched')
                except ValueError:pass
            record={'source_id':req['id'],'bbox_lonlat':req['research_bbox_lonlat'],'query_complete':good,'http_status':req.get('http_status')}
            records.append(record)
            invalid_ring=req.get('http_status')==400 and b'LinearRing' in body
            if invalid_ring and depth<3:pending.append((req['research_bbox_lonlat'],req['id'].split('tactile-',1)[1]))
            else:leaves.append(record)
    gaps=[x for x in leaves if not x['query_complete']]
    result={'requests':len(records),'max_split_depth':3,'initial_failed_bbox_lonlat':[127.335,36.63,127.39,36.67],
      'leaf_extents':leaves,'unretrieved_extent_count':len(gaps),'unretrieved_extents':gaps,
      'source_geometry_repaired':False,'unknown_areas_treated_as_zero':False,'field_verified':False,'routing_eligible':False}
    target.write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n')
    print(json.dumps({'requests':len(records),'successful_leaf_extents':sum(x['query_complete'] for x in leaves),'unretrieved_leaf_extents':len(gaps)},ensure_ascii=False),flush=True)
if __name__=='__main__':main()
