export const unavailableTransitPaths = new Set(['/api/routes/transit','/api/transit/status','/api/transit/walk-review','/api/journeys']);
// A server-side build boundary: changing browser controls cannot enable a key.
export function walkOnlyResponse(req,res,route) {
  if(!unavailableTransitPaths.has(route))return false;
  const status=route==='/api/transit/status';
  res.writeHead(status?200:404,{'Content-Type':'application/json; charset=utf-8','Cache-Control':'no-store','X-Content-Type-Options':'nosniff'});
  res.end(JSON.stringify(status?{state:'unavailable_in_web_build',used:0,citywide:false,fieldVerified:false,scheduleValidation:false,notice:'도보 공개판에서는 대중교통을 제공하지 않습니다.'}:{code:'transit_not_in_web_build',error:'도보 공개판에서는 대중교통을 제공하지 않습니다.'}));
  return true;
}
