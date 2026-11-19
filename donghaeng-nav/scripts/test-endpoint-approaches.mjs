import assert from 'node:assert/strict';
import {createRequire} from 'node:module';
import {createCityWalkService, distance} from '../services/city-walk/router.mjs';
const require=createRequire(import.meta.url);
const E=require('../dist/engine'),X=require('../dist/endpoint-routing');

const localNodes=new Map([[1,{tags:{},edges:[]}],[2,{tags:{},edges:[{to:3,key:'stairs',d:5,steps:true},{to:4,key:'walking',d:12}]}],[3,{tags:{},edges:[]}],[4,{tags:{},edges:[]}]]);
const selected=E.shortestApproaches({nodes:localNodes},new Map([[1,0],[2,8]]),new Map([[3,0],[4,3]]),{avoidSteps:true});
assert.deepEqual(selected.ids,[2,4]);
assert.equal(selected.cost,12);
assert.equal(selected.length,12);
assert.deepEqual(E.shortestApproaches({nodes:localNodes},new Map([[2,8]]),new Map([[3,0],[4,3]]),{}).ids,[2,3]);
const gapGraph={nodes:new Map([
 [1,{tags:{},edges:[{to:3,key:'short',d:9}]}],
 [2,{tags:{},edges:[{to:4,key:'long',d:12}]}],
 [3,{tags:{},edges:[]}],[4,{tags:{},edges:[]}]
])};
assert.deepEqual(E.shortestApproaches(gapGraph,new Map([[1,3],[2,4]]),new Map([[3,10],[4,1]]),{}).ids,[2,4]);

const points=[[37.5665,126.978],[37.5665,126.9786],[37.5665,126.9796],[37.56665,126.978],[37.56665,126.9775]];
function makeCity(parts,stairs=[]) {
 const targets=[],indices=[],offsets=[0];
 for(let i=0;i<points.length;i++){
  for(const [edge,[a,b]] of parts.entries())if(i===a||i===b){targets.push(i===a?b:a);indices.push(edge);}
  offsets.push(targets.length);
 }
 const cells=new Map();
 points.forEach(([lat,lon],index)=>{
  const key=Math.floor(lon/.005)+':'+Math.floor(lat/.005);
  if(!cells.has(key))cells.set(key,[]);
  cells.get(key).push(index);
 });
 const graph={m:{nodes:points.length},coordinates:Float64Array.from(points.flatMap(([lat,lon])=>[lon,lat])),
  nodeIds:Uint32Array.from([10,11,12,13,14]),offsets:Uint32Array.from(offsets),targets:Uint32Array.from(targets),
  edgeIndices:Uint32Array.from(indices),lengths:Float64Array.from(parts.map(([a,b])=>distance(points[a],points[b]))),
  flags:Uint8Array.from(parts.map((_,i)=>stairs.includes(i)?1:0)),slopes:new Float64Array(parts.length).fill(NaN),
  wayIndex:Uint32Array.from(parts.map((_,i)=>i)),parts:new Uint32Array(parts.length),ways:parts.map((_,i)=>[101+i,'fixture']),cells};
 return createCityWalkService({graph:{manifest:async()=>({bounds:[126.75,37.4,127.2,37.72]}),load:async()=>graph}});
}
const origin=[37.5665,126.9782], request={origin,destination:points[2],profile:{avoidSteps:true}};
const city=makeCity([[0,1],[1,2],[3,4]]);
const improved=await city.route(request);
assert.deepEqual(improved.sourceNodeIds,[11,12]);
assert.deepEqual(improved.sourceSegments,[[102,0]]);
assert.equal(improved.approachesOnRoad[0].wayId,101);
assert(improved.offNetworkGaps[0]<.1);
const baseline=distance(origin,points[0])+distance(points[0],points[1])+distance(points[1],points[2]);
assert(baseline-improved.totalReferenceMeters>30);
assert(improved.totalReferenceMeters>improved.distanceMeters);
assert.equal(improved.endpointConnectionsVerified,false);
await assert.rejects(city.route({...request,origin:points[3]}),{code:'city_no_connected_route'});
await assert.rejects(makeCity([[0,1],[1,2],[3,4]],[1]).route(request),{code:'city_endpoint_unresolved'});
await assert.rejects(city.route({...request,profile:{maxSlope:5}}),{code:'city_endpoint_unresolved'});

// Nearby parallel roads stay distinct and require the original pin review.
const parallel={nodes:new Map(),main:new Set(),meta:{}};
for(const [i,y] of [37.5665,37.5666].entries()){
 const a=10+i*2,b=a+1;
 parallel.nodes.set(a,{id:a,ll:[y,126.978],edges:[{id:100+i,key:String(i),to:b}]});
 parallel.nodes.set(b,{id:b,ll:[y,126.979],edges:[{id:100+i,key:String(i),to:a}]});
 parallel.main.add(a);parallel.main.add(b);
}
assert.throws(()=>X.nearestSegment(parallel,[37.56655,126.9785]),/평행 도로/);
console.log(JSON.stringify({pass:true,syntheticDistanceBefore:Math.round(baseline),syntheticDistanceAfter:Math.round(improved.totalReferenceMeters),newGraphEdges:0,fieldVerified:false}));
