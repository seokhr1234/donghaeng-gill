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

const localCityPoints=[[37.5665,126.978],[37.5665,126.9786],[37.5665,126.9796],[37.56665,126.978],[37.56665,126.9775]];
function makeCity(parts,stairs=[],points=localCityPoints,slopes=[],busy=[]) {
 const targets=[],indices=[],offsets=[0];
 for(let i=0;i<points.length;i++){
  for(const [edge,[a,b]] of parts.entries())if(i===a||i===b){targets.push(i===a?b:a);indices.push(edge);}
  offsets.push(targets.length);
 }

 const graph={m:{nodes:points.length},coordinates:Float64Array.from(points.flatMap(([lat,lon])=>[lon,lat])),
  nodeIds:Uint32Array.from(points.map((_,i)=>10+i)),offsets:Uint32Array.from(offsets),targets:Uint32Array.from(targets),
  edgeIndices:Uint32Array.from(indices),starts:Uint32Array.from(parts.map(([a])=>a)),ends:Uint32Array.from(parts.map(([,b])=>b)),lengths:Float64Array.from(parts.map(([a,b])=>distance(points[a],points[b]))),
  flags:Uint8Array.from(parts.map((_,i)=>(stairs.includes(i)?1:0)|(busy.includes(i)?2:0))),slopes:Float64Array.from(parts.map((_,i)=>slopes[i]??NaN)),
  wayIndex:Uint32Array.from(parts.map((_,i)=>i)),parts:new Uint32Array(parts.length),ways:parts.map((_,i)=>[101+i,'fixture'])};
 return createCityWalkService({graph:{manifest:async()=>({bounds:[126.75,37.4,127.2,37.72]}),load:async()=>graph}});
}
const origin=[37.5665,126.9782], request={origin,destination:localCityPoints[2],profile:{avoidSteps:true}};
const city=makeCity([[0,1],[1,2],[3,4]]);
const improved=await city.route(request);
assert.deepEqual(improved.sourceNodeIds,[11,12]);
assert.deepEqual(improved.sourceSegments,[[102,0]]);
assert.equal(improved.approachesOnRoad[0].wayId,101);
assert(improved.offNetworkGaps[0]<.1);
const baseline=distance(origin,localCityPoints[0])+distance(localCityPoints[0],localCityPoints[1])+distance(localCityPoints[1],localCityPoints[2]);
assert(baseline-improved.totalReferenceMeters>30);
assert(improved.totalReferenceMeters>improved.distanceMeters);
assert.equal(improved.endpointConnectionsVerified,false);
await assert.rejects(city.route({...request,origin:localCityPoints[3]}),{code:'city_no_connected_route'});
await assert.rejects(makeCity([[0,1],[1,2],[3,4]],[1]).route(request),{code:'city_endpoint_unresolved'});
await assert.rejects(city.route({...request,profile:{maxSlope:5}}),{code:'city_endpoint_unresolved'});

// A pair of points in the middle of a road can be far from either OSM node.
const longRoad=[[37.5665,126.95],[37.5665,126.99]];
const longTrip={origin:[37.5665,126.969],destination:[37.5665,126.971],profile:{wheelchair:true}};
const midpointCity=makeCity([[0,1]],[],longRoad);
const midpoint=await midpointCity.route(longTrip,{allowUnknownSlopeFallback:true});
assert.equal(midpoint.slopeFallback,true);
assert.equal(midpoint.accessibilityVerified,false);
assert.equal(midpoint.stepsMeters,0);
assert.equal(midpoint.registeredInclineMax,null);
assert(Math.abs(midpoint.distanceMeters-distance(longTrip.origin,longTrip.destination))<.01);
assert(Math.abs(midpoint.unknownInclineMeters-midpoint.distanceMeters)<.01);
assert(midpoint.offNetworkGaps.every(gap=>gap<.01));
assert.deepEqual(midpoint.sourceSegments,[[101,0]]);
assert(midpoint.coordinates.every((point,i)=>distance(point,[longTrip.origin,longTrip.destination][i])<.01));
await assert.rejects(midpointCity.route({...longTrip,destination:longTrip.origin},{allowUnknownSlopeFallback:true}),{code:'same_endpoint'});
const tooSteep=makeCity([[0,1]],[],longRoad,[8]);
await assert.rejects(tooSteep.route(longTrip,{allowUnknownSlopeFallback:true}),{code:'city_endpoint_unresolved'});
const stairs=makeCity([[0,1]],[0],longRoad);
await assert.rejects(stairs.route(longTrip,{allowUnknownSlopeFallback:true}),{code:'city_endpoint_unresolved'});

// With missing grades, the fallback uses distance in place of road-type penalties.
const choiceNodes=[[37.56,126.9799],[37.56,126.98],[37.56,126.982],[37.5604,126.981],[37.56,126.9821]];
const choice=makeCity([[0,1],[1,2],[1,3],[3,2],[2,4]],[],choiceNodes,[],[1]);
const choiceTrip={origin:choiceNodes[0],destination:choiceNodes[4]};
const quietRoute=await choice.route(choiceTrip);
const shortest=await choice.route({...choiceTrip,profile:{wheelchair:true}},{allowUnknownSlopeFallback:true});
assert(quietRoute.sourceSegments.some(([way])=>way===103));
assert(shortest.sourceSegments.some(([way])=>way===102));
assert(shortest.distanceMeters<quietRoute.distanceMeters);

// Two partial segments meeting at a shared OSM node form a route of their own.
const cornerNodes=[[37.56,126.98],[37.56,126.981],[37.561,126.981]];
const cornerCity=makeCity([[0,1],[1,2]],[],cornerNodes);
const cornerTrip={origin:[37.56,126.9808],destination:[37.5602,126.981]};
const corner=await cornerCity.route(cornerTrip);
assert.equal(corner.coordinates.length,3);
assert.deepEqual(corner.sourceNodeIds,[10,11,12]);
assert(Math.abs(corner.distanceMeters-distance(cornerTrip.origin,cornerNodes[1])-distance(cornerNodes[1],cornerTrip.destination))<.01);

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
