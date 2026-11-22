(function(root,factory){
 if(typeof module==='object'&&module.exports)module.exports=factory();else root.DeviceHeading=factory();
})(globalThis,function(){
'use strict';
const wrap=value=>(value%360+360)%360;
function fromEvent(event,angle=0){
 if(Number.isFinite(event.webkitCompassHeading)){
  if(Number.isFinite(event.webkitCompassAccuracy)&&(event.webkitCompassAccuracy<0||event.webkitCompassAccuracy>45))return null;
  return wrap(event.webkitCompassHeading+angle);
 }
 if(event.absolute!==true||!Number.isFinite(event.alpha))return null;
 return wrap(360-event.alpha+angle);
}
function create({target=globalThis,now=()=>Date.now(),timers=globalThis,onUpdate=()=>{}}={}){
 let state={active:false,phase:'off',degrees:null},version=0,timer=null,last=0,removeNative=null,permission=false;
 const emit=()=>onUpdate({...state});
 function clear(){
  version++;target.removeEventListener('deviceorientation',orientation);target.removeEventListener('deviceorientationabsolute',orientation);
  if(timer!==null)timers.clearInterval(timer);timer=null;
  removeNative?.();removeNative=null;
 }
 function stop(){clear();state={active:false,phase:'off',degrees:null};emit();}
 function accept(value,reliable=true){
  if(!state.active)return;
  if(!reliable||!Number.isFinite(value)){state={...state,phase:'calibrating',degrees:null};emit();return;}
  const heading=wrap(value),previous=state.degrees;
  last=now();state={active:true,phase:'tracking',degrees:previous===null?heading:wrap(previous+((heading-previous+540)%360-180)*.35)};emit();
 }
 function orientation(event){
  const angle=target.screen?.orientation?.angle??target.orientation??0;
  const value=fromEvent(event,Number.isFinite(angle)?angle:0);
  if(value!==null)accept(value);
  else if(Number.isFinite(event.webkitCompassAccuracy)&&(event.webkitCompassAccuracy<0||event.webkitCompassAccuracy>45))accept(null,false);
 }
 async function start(){
  clear();const generation=version;state={active:true,phase:'waiting',degrees:null};last=now();emit();
  if(target.isSecureContext===false){state={active:false,phase:'insecure',degrees:null};emit();return false;}
  try{
   if(target.DonghaengHeading){
    const remove=await target.DonghaengHeading.start(value=>accept(value.degrees,value.reliable));
    if(version!==generation){remove();return false;}removeNative=remove;
   }else{
    const API=target.DeviceOrientationEvent;
    if(!API){state={active:false,phase:'unsupported',degrees:null};emit();return false;}
    if(typeof API.requestPermission==='function'&&!permission){
     // Called synchronously from the direction button's click handler.
     const result=await API.requestPermission(true);
     if(version!==generation)return false;
     if(result!=='granted'){state={active:false,phase:'denied',degrees:null};emit();return false;}
     permission=true;
    }
    if(version!==generation)return false;
    target.addEventListener('deviceorientationabsolute',orientation);
    target.addEventListener('deviceorientation',orientation);
   }
   timer=timers.setInterval(()=>{
    if(now()-last>6000&&state.phase!=='stale'){state={...state,phase:'stale',degrees:null};emit();}
   },1000);
   return true;
  }catch{
   if(version!==generation)return false;
   clear();state={active:false,phase:'unavailable',degrees:null};emit();return false;
  }
 }
 return {start,stop,snapshot:()=>({...state})};
}
return {create,fromEvent,wrap};
});
