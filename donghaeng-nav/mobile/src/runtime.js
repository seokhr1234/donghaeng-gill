import {registerPlugin} from '@capacitor/core';
import {Geolocation} from '@capacitor/geolocation';
import {walkingInput,ServiceError} from '../../services/expansion/contracts.mjs';
import {normalizeOdsay,transitDistance,shortTransitError} from '../../services/transit/odsay.mjs';
import {createWalkReviewService} from '../../services/transit/walk-review.mjs';
import {setupApiSettings} from './api-settings.js';
const bridge=registerPlugin('Donghaeng'),originalFetch=globalThis.fetch.bind(globalThis);
const review=createWalkReviewService(),id=()=>crypto.randomUUID().replaceAll('-','');
let deviceGeminiConfigured=false;
async function readSettings(){const s=await bridge.status();deviceGeminiConfigured=s.geminiConfigured===true;return s;}
globalThis.DonghaengAndroidAI=Object.freeze({get deviceKey(){return deviceGeminiConfigured;}});
async function native(method,options,signal){
 signal?.throwIfAborted();const requestId=id(),abort=()=>{bridge.cancel({requestId}).catch(()=>{})};signal?.addEventListener('abort',abort,{once:true});
 try{const result=await bridge[method]({...options,requestId});signal?.throwIfAborted();return result}finally{signal?.removeEventListener('abort',abort)}
}
function json(raw){try{return JSON.parse(raw)}catch{throw new ServiceError(502,'native_invalid_response','서버 응답을 읽지 못했어요.')}}
async function geminiResponse(path,input,signal){
 const selecting=path==='/api/select-route';let clean;
 if(selecting){try{clean=globalThis.RouteChoice.validateInput(input);}catch{throw new ServiceError(400,'invalid_candidates','경로 비교 요청을 확인해 주세요.');}}
 else{if(!input||Array.isArray(input)||Object.keys(input).some(k=>k!=='condition')||typeof input.condition!=='string'||!input.condition.trim()||input.condition.length>500)throw new ServiceError(400,'invalid_condition','상태 문장을 1~500자로 입력해 주세요.');clean={condition:input.condition.trim()};}
 const request=selecting?globalThis.RouteChoice.request(clean):globalThis.ConditionRequest.create(clean.condition);
 const r=await native('gemini',{model:globalThis.ConditionRequest.defaultModel,request},signal);
 if(r.status!==200){const error=json(r.body);throw new ServiceError(r.status,error.code||'gemini_failed',error.error||'Gemini 키와 모델 설정을 확인해 주세요.');}
 try{const data=json(r.body),text=data.candidates?.[0]?.content?.parts?.filter(p=>!p.thought).map(p=>p.text||'').join(''),value=JSON.parse(text);
  return selecting?{decision:globalThis.RouteChoice.validateDecision(value,clean.candidates),source:'Gemini',keySource:'android-device'}:{profile:globalThis.ConditionAI.validate(value),source:'Gemini',keySource:'android-device'};
 }catch{throw new ServiceError(502,'gemini_response_invalid','Gemini 응답 형식을 확인하지 못했어요.');}
}
globalThis.DonghaengAndroidBackend=async(path,input,{signal}={})=>{const r=await native('backend',{path,method:input?'POST':'GET',body:input?JSON.stringify(input):''},signal),data=json(r.body);if(r.status<200||r.status>=300)throw new ServiceError(r.status,data.code||'backend_unavailable',data.error||'서버 연결을 완료하지 못했어요.');return data};
globalThis.fetch=async(resource,options={})=>{
 const url=new URL(typeof resource==='string'?resource:resource.url,location.href);if(url.origin!==location.origin||!url.pathname.startsWith('/api/'))return originalFetch(resource,options);
 const signal=options.signal;signal?.throwIfAborted();
 const respond=(data,status=200)=>new Response(JSON.stringify(data),{status,headers:{'Content-Type':'application/json','Cache-Control':'no-store'}});
 try{
  if(url.pathname==='/api/transit/status'){const s=await readSettings();return respond({state:s.configured?'reference_candidates_only':'not_configured',used:s.used,dailyLimit:s.dailyLimit,budgetScope:'android_device',fieldVerified:false,scheduleValidation:false})}
  if(['/api/status','/api/analyze-condition','/api/select-route'].includes(url.pathname)){
   const settings=await readSettings();
   if(settings.geminiConfigured){
    if(url.pathname==='/api/status')return respond({configured:true,provider:'Gemini',model:globalThis.ConditionRequest?.defaultModel||null,keySource:'android-device'});
    if((options.method||'GET')!=='POST')return respond({error:'POST 요청을 사용해 주세요.'},405);
    let input;try{input=JSON.parse(options.body);}catch{throw new ServiceError(400,'invalid_json','JSON 요청을 확인해 주세요.');}
    return respond(await geminiResponse(url.pathname,input,signal));
   }
  }
  if(url.pathname==='/api/routes/transit'){
   const input=walkingInput(JSON.parse(options.body));if(transitDistance(input.origin,input.destination)<=700)throw shortTransitError();
   const r=await native('search',{origin:input.origin,destination:input.destination},signal);if(r.status!==200)throw new ServiceError(r.status,'android_transit_unavailable','대중교통 검색에 실패했어요. 오른쪽 위 교통 키 설정과 인터넷 연결을 확인해 주세요.');return respond(normalizeOdsay(json(r.body),input));
  }
  if(url.pathname==='/api/transit/walk-review')return respond(await review.review(JSON.parse(options.body),{signal}));
  const r=await native('backend',{path:url.pathname+url.search,method:options.method||'GET',body:options.body||''},signal);return new Response(r.body,{status:r.status,headers:{'Content-Type':'application/json'}});
 }catch(e){signal?.throwIfAborted();return respond({code:e.code||'android_service_unavailable',error:e.status?e.message:'앱 연결에 실패했어요. 교통 키와 인터넷 연결을 확인해 주세요.',...(e.providerCode?{providerCode:e.providerCode}:{})},e.status&&e.status>=400&&e.status<=599?e.status:503)}
};
// Preserve the original filter/accuracy handling: only replace the device source.
const locationError=e=>({code:/denied|0003/i.test(String(e?.message||e?.code))?1:2,message:'위치 권한과 기기의 위치 서비스를 확인해 주세요.'});
const watches=new Map();let serial=0;
async function permitted(){const p=await Geolocation.checkPermissions();if(p.location!=='granted'){const next=await Geolocation.requestPermissions({permissions:['location']});if(next.location!=='granted')throw Error('denied')}}
Object.defineProperty(navigator,'geolocation',{value:{
 getCurrentPosition(ok,error,options={}){permitted().then(()=>Geolocation.getCurrentPosition(options)).then(ok,e=>error?.(locationError(e)))},
 watchPosition(ok,error,options={}){const key=++serial;const promise=permitted().then(()=>Geolocation.watchPosition(options,(p,e)=>e?error?.(locationError(e)):p&&ok(p)));watches.set(key,promise);promise.catch(e=>error?.(locationError(e)));return key},
 clearWatch(key){const p=watches.get(key);watches.delete(key);p?.then(id=>Geolocation.clearWatch({id})).catch(()=>{})}
},configurable:true});
window.addEventListener('pagehide',()=>{for(const key of watches.keys())navigator.geolocation.clearWatch(key)});
window.addEventListener('DOMContentLoaded',()=>{
 readSettings().catch(()=>{});
 setupApiSettings({bridge,native,getStatus:readSettings,onChanged:s=>{deviceGeminiConfigured=s.geminiConfigured===true;globalThis.conditionChanged?.();globalThis.refreshTransitStatus?.();}});
});
