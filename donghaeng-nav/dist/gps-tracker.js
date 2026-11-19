(function(root){'use strict';
const Quality=typeof module!=='undefined'?require('./gps-quality.js'):root.GPSQuality;
function create({geolocation=globalThis.navigator?.geolocation,now=()=>Date.now(),timers=globalThis,onUpdate=()=>{}}={}){
 const guidanceQuality=Quality.create(),displayQuality=Quality.createDisplay();
 let watch=null,timer=null,version=0,state=empty('idle');
 function empty(phase){return {active:false,phase,fix:null,displayFix:null,originFix:null,ageSeconds:0}}
 const emit=()=>{onUpdate({...state});return {...state}};
 function clear(){
  guidanceQuality.reset();displayQuality.reset();version++;
  if(watch!==null)geolocation?.clearWatch(watch);
  if(timer!==null)timers.clearInterval(timer);
  watch=timer=null;
 }
 function stop(){clear();state=empty('stopped');return emit()}
 function start(){
  clear();state=empty('waiting');
  if(!geolocation){state.phase='unsupported';emit();return false}
  state.active=true;const generation=version;emit();
  timer=timers.setInterval(()=>{
   if(generation!==version||!state.fix)return;
   const age=now()-state.fix.timestamp;
   if(age>=Quality.displayStaleMs){
    state={...state,phase:'stale',originFix:null,ageSeconds:Math.floor(age/1000)};
    emit();
   }
  },1000);
  try{
   const id=geolocation.watchPosition(pos=>{
    if(generation!==version)return;
    const c=pos.coords,time=now(),sample={latitude:c.latitude,longitude:c.longitude,accuracy:c.accuracy,heading:c.heading,speed:c.speed,timestamp:pos.timestamp};
    const display=displayQuality.consume(sample,time),origin=guidanceQuality.consume(sample,time);
    if(display.reason==='duplicate')return;
    if(!display.accepted){
     state={...state,phase:'acquiring',originFix:null,qualityMessage:display.message};emit();return;
    }
    state={active:true,phase:display.raw.accuracy>Quality.approximateAccuracy?'approximate':'tracking',fix:display.raw,displayFix:display.display,originFix:origin.accepted?origin.raw:null,ageSeconds:0};
    emit();
   },err=>{
    if(generation!==version)return;
    if(err.code===1){clear();state=empty('denied')}
    else state={...state,phase:err.code===3?'timeout':'unavailable',originFix:null,ageSeconds:state.fix?Math.max(0,Math.floor((now()-state.fix.timestamp)/1000)):0};
    emit();
   },{enableHighAccuracy:true,maximumAge:0,timeout:15000});
   if(version===generation)watch=id;else geolocation.clearWatch(id);
  }catch{clear();state=empty('unavailable');emit();return false}
  return state.active;
 }
 return {start,stop,snapshot:()=>({...state})};
}
const api={create};if(typeof module!=='undefined')module.exports=api;else root.GPSTracker=api;
})(typeof globalThis==='undefined'?this:globalThis);
