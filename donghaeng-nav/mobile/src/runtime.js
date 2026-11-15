import {registerPlugin} from '@capacitor/core';
import {Geolocation} from '@capacitor/geolocation';
import {walkingInput,ServiceError} from '../../services/expansion/contracts.mjs';
import {normalizeOdsay,transitDistance,shortTransitError} from '../../services/transit/odsay.mjs';
import {createWalkReviewService} from '../../services/transit/walk-review.mjs';
const bridge=registerPlugin('Donghaeng'),originalFetch=globalThis.fetch.bind(globalThis);
const review=createWalkReviewService(),id=()=>crypto.randomUUID().replaceAll('-','');
async function native(method,options,signal){
 signal?.throwIfAborted();const requestId=id(),abort=()=>{bridge.cancel({requestId}).catch(()=>{})};signal?.addEventListener('abort',abort,{once:true});
 try{const result=await bridge[method]({...options,requestId});signal?.throwIfAborted();return result}finally{signal?.removeEventListener('abort',abort)}
}
function json(raw){try{return JSON.parse(raw)}catch{throw new ServiceError(502,'native_invalid_response','서버 응답을 읽지 못했어요.')}}
globalThis.DonghaengAndroidBackend=async(path,input,{signal}={})=>{const r=await native('backend',{path,method:input?'POST':'GET',body:input?JSON.stringify(input):''},signal),data=json(r.body);if(r.status<200||r.status>=300)throw new ServiceError(r.status,data.code||'backend_unavailable',data.error||'서버 연결을 완료하지 못했어요.');return data};
globalThis.fetch=async(resource,options={})=>{
 const url=new URL(typeof resource==='string'?resource:resource.url,location.href);if(url.origin!==location.origin||!url.pathname.startsWith('/api/'))return originalFetch(resource,options);
 const signal=options.signal;signal?.throwIfAborted();
 const respond=(data,status=200)=>new Response(JSON.stringify(data),{status,headers:{'Content-Type':'application/json','Cache-Control':'no-store'}});
 try{
  if(url.pathname==='/api/transit/status'){const s=await bridge.status();return respond({state:s.configured?'reference_candidates_only':'not_configured',used:s.used,dailyLimit:s.dailyLimit,budgetScope:'android_device',fieldVerified:false,scheduleValidation:false})}
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
window.addEventListener('DOMContentLoaded',()=>{const button=document.createElement('button');button.type='button';button.textContent='교통 키';button.title='ODsay Android 키 설정';button.className='secondary android-key-button';button.style.cssText='font-size:11px;padding:6px 9px;min-height:36px;border-radius:12px;margin-left:auto';button.onclick=async()=>{await bridge.configureKey();globalThis.refreshTransitStatus?.()};document.querySelector('.header')?.append(button)});
