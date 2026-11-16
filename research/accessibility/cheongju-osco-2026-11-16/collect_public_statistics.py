#!/usr/bin/env python3
"""Use the municipality's normal anonymous UI session for public read-only statistics."""
from pathlib import Path
import datetime as dt,hashlib,http.cookiejar,json,urllib.error,urllib.parse,urllib.request
from lxml import html
ROOT=Path(__file__).resolve().parent
KST=dt.timezone(dt.timedelta(hours=9))
opener=urllib.request.build_opener(urllib.request.HTTPCookieProcessor(http.cookiejar.CookieJar()))

def fetch(ident,url,form=None,csrf=None):
    folder=ROOT/'raw'/ident;folder.mkdir(parents=True,exist_ok=False)
    headers={'User-Agent':'DonghaengAccessibilityResearch/1.0'}
    sent=dict(form or {})
    if csrf:sent['_csrf']=csrf
    body=urllib.parse.urlencode(sent).encode() if form is not None else None
    if body is not None:headers['Content-Type']='application/x-www-form-urlencoded'
    req=urllib.request.Request(url,data=body,headers=headers)
    record={'id':ident,'url':url,'method':'POST' if body is not None else 'GET',
      'form_without_csrf_token':form,'public_anonymous_session':True,'login_attempted':False,
      'csrf_parameter_sent':bool(csrf),'csrf_token_in_request_log':False,
      'requested_at_utc':dt.datetime.now(dt.timezone.utc).isoformat(),
      'requested_at_kst':dt.datetime.now(KST).isoformat(),'field_verified':False,'source_as_of':None,
      'source_crs':None,'vertical_datum':None}
    data=b''
    try:
        try:response=opener.open(req,timeout=35)
        except urllib.error.HTTPError as e:response=e
        with response:
            record['http_status']=response.code;record['final_url']=response.url
            record['response_headers']={k:v for k,v in response.headers.items() if k.lower() in ['content-type','content-length','date','last-modified']}
            data=response.read()
        (folder/'response.bin').write_bytes(data)
        record.update(bytes=len(data),sha256=hashlib.sha256(data).hexdigest(),response_path=str((folder/'response.bin').relative_to(ROOT)),transport_result='http_response')
    except Exception as e:record.update(http_status=None,transport_result='request_failed',error_type=type(e).__name__,error=str(e))
    record['completed_at_utc']=dt.datetime.now(dt.timezone.utc).isoformat()
    (folder/'request.json').write_text(json.dumps(record,ensure_ascii=False,indent=2)+'\n')
    print(json.dumps({k:record.get(k) for k in ['id','http_status','bytes','error']},ensure_ascii=False),flush=True)
    return record,data

def main():
    rec,body=fetch('cheongju-tgis-anonymous-seed','https://www.cjtgis.go.kr/statistics/selectRodInfo.do')
    if rec.get('http_status')!=200:return
    d=html.fromstring(body.decode('utf-8'));tokens=d.xpath('//meta[@name="_csrf"]/@content')
    token=tokens[0] if tokens else None
    # Only endpoints and facility IDs linked by the public anonymous UI are used.
    fetch('cheongju-tgis-public-menu-post','https://www.cjtgis.go.kr/system/menu/userMenu.json',{},token)
    for name,code in [('tactile','GT_C094_A'),('crossings','GT_A004_A'),('audible','GT_A119_P'),('grade-crossings','GT_C095_A'),('ground-signals','GT_A089_A')]:
        rec,_=fetch('cheongju-tgis-statistics-json-'+name,'https://www.cjtgis.go.kr/statistics/selectStatisticsInfo.json',{'facilityId':code},token)
        if rec.get('http_status') in [401,403]:break
if __name__=='__main__':main()
