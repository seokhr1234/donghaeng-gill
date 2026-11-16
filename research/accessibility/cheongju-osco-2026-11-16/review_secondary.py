#!/usr/bin/env python3
"""Audit public mirror pages without executing JavaScript or promoting their claims."""
from pathlib import Path
import collections,csv,json,math,re
from lxml import html

ROOT=Path(__file__).resolve().parent
def meters(a,b):
    lat,lon,lat2,lon2=map(math.radians,(*a,*b))
    q=math.sin((lat2-lat)/2)**2+math.cos(lat)*math.cos(lat2)*math.sin((lon2-lon)/2)**2
    return 12742000*math.asin(min(1,math.sqrt(q)))
def page_markers(folder):
    path=ROOT/'raw'/folder/'response.bin';d=html.fromstring(path.read_bytes());records={}
    def walk(v):
        if isinstance(v,dict):
            if {'id','lat','lng','label'}.issubset(v):records[v['id']]=dict(v,source_id=folder)
            for x in v.values():walk(x)
        elif isinstance(v,list):
            for x in v:walk(x)
    for script in d.xpath('//script'):
        s=(script.text or '').strip().rstrip(';')
        if not s.startswith('self.__next_f.push('):continue
        try:j=json.loads(s[len('self.__next_f.push('):-1])
        except ValueError:continue
        if len(j)<2 or not isinstance(j[1],str):continue
        for line in j[1].splitlines():
            if ':' not in line:continue
            body=line.split(':',1)[1]
            if not body.startswith(('[','{')):continue
            try:walk(json.loads(body))
            except ValueError:pass
    visible={}
    for x in d.xpath('//*[@data-map-id]'):
        ident=x.get('data-map-id')
        text=' '.join(' '.join(x.itertext()).split())
        if text:visible[ident]=text
    for ident,obj in records.items():obj['visible_summary']=visible.get(ident)
    return records,visible
def main():
    out=ROOT/'secondary-derived';out.mkdir(exist_ok=True)
    center=(36.6267203,127.335363)
    toilets={};visible={};coordinate_conflicts=[]
    folders=['secondary-toilets-heungdeok']+[p.name for p in sorted((ROOT/'raw').glob('secondary-toilets-page-*'))]
    for folder in folders:
        markers,rows=page_markers(folder);visible.update(rows)
        for ident,obj in markers.items():
            if ident in toilets and [toilets[ident]['lat'],toilets[ident]['lng']]!=[obj['lat'],obj['lng']]:coordinate_conflicts.append(ident)
            toilets[ident]=obj
    near_toilets=[]
    for obj in toilets.values():
        distance=meters(center,(obj['lat'],obj['lng']))
        if distance<=5000:near_toilets.append(dict(obj,distance_straight_line_m=round(distance,1),coordinate_basis='secondary website display marker; official coordinate provenance unverified',field_verified=False,routing_eligible=False))
    rows=list(csv.DictReader((ROOT/'raw/secondary-heat-csv/response.bin').read_text(encoding='utf-8-sig').splitlines()))
    near_shelters=[]
    for obj in rows:
        try:distance=meters(center,(float(obj['lat']),float(obj['lng'])))
        except (ValueError,TypeError):continue
        if distance<=5000:near_shelters.append(dict(obj,distance_straight_line_m=round(distance,1),raw_official_verified=False,blank_flags_are_unknown=True,license_verified=False,field_verified=False,routing_eligible=False))
    heat_markers,heat_visible=page_markers('secondary-heat-osong-neighborhood')
    normalize=lambda s:re.sub(r'\s+','',s)
    by_name=collections.defaultdict(list)
    for row in rows:
        if '청주시' in row.get('addr','') and '오송읍' in row.get('addr',''):by_name[normalize(row['name'])].append(row)
    comparisons=[]
    for marker in heat_markers.values():
        candidates=by_name.get(normalize(marker['label']),[])
        if len(candidates)==1:
            row=candidates[0]
            delta=meters((marker['lat'],marker['lng']),(float(row['lat']),float(row['lng'])))
            comparisons.append({'name':marker['label'],'mirror_csv_id':row['id'],'other_mirror_id':marker['id'],'coordinate_separation_m':round(delta,1),'match_method':'name plus Cheongju Osong address in CSV; tentative, not confirmed physical identity','identity_verified':False})
    for name,value in [('toilet-display-markers-near5km.json',near_toilets),('shelter-mirror-near5km.json',near_shelters),('heat-osong-other-mirror.json',list(heat_markers.values()))]:
        (out/name).write_text(json.dumps(value,ensure_ascii=False,indent=2)+'\n')
    summary={'secondary_source_only':True,'toilet_pages_collected':len(folders),'toilet_visible_ids':len(visible),'toilet_display_marker_ids':len(toilets),'toilet_display_coordinate_conflicts':coordinate_conflicts,
      'toilet_markers_within_5km':len(near_toilets),'heat_csv_total':len(rows),'heat_csv_within_5km':len(near_shelters),'heat_osong_other_mirror_visible_ids':len(heat_visible),'heat_osong_other_mirror_markers':len(heat_markers),
      'heat_name_match_coordinate_comparisons':comparisons,
      'within_meters':{str(d):{'toilet_display_markers':sum(x['distance_straight_line_m']<=d for x in near_toilets),'shelter_mirror_csv_rows':sum(x['distance_straight_line_m']<=d for x in near_shelters)} for d in [1000,2000,5000]},
      'provenance_conflicts':['Shelter HTML total62704 differs from downloaded CSV62694','Shelter page collected date2026-11-08 predates claimed source date2026-11-09','Shelter page claims17 provinces and16 provinces in different sections','Mirror explicitly states licence unconfirmed','Current official toilet standard says coordinates stopped in2025; mirror coordinate source needs independent verification','Blank flags mean unknown; name match alone does not prove same physical facility'],
      'runtime_import_allowed':False,'raw_official_dataset_verified':False,'license_verified':False,'full_secondary_rows_in_git':False,'field_verified':False}
    (ROOT/'secondary-facilities-review.json').write_text(json.dumps(summary,ensure_ascii=False,indent=2)+'\n')
    print(json.dumps({k:summary[k] for k in ['toilet_visible_ids','toilet_display_marker_ids','toilet_markers_within_5km','heat_csv_within_5km','heat_osong_other_mirror_markers','within_meters']},ensure_ascii=False))
    print('Mirror coordinate comparisons',json.dumps(comparisons,ensure_ascii=False))
if __name__=='__main__':main()
