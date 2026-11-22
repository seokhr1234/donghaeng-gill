import assert from 'node:assert/strict';
import {createRequire} from 'node:module';
import {createApp} from '../server.mjs';
import {walkingInput} from '../services/expansion/contracts.mjs';

const require = createRequire(import.meta.url);
const E = require('../dist/engine.js');
const Beta = require('../dist/demo-beta.js');
const Endpoint = require('../dist/endpoint-routing.js');
const {chromium} = require('playwright');
const shelter = {id: 'closed', kind: 'shelter', geometry: {type: 'Point', coordinates: [127.04, 37.59]},
  properties: {name: '등록 쉼터', official_hours_conflict: true, operation: 'closed', access: 'private'}};
const [candidate] = Beta.places([shelter, {...shelter, geometry: null}]);
assert.equal(candidate.id, 'closed');
for (const properties of [{access: 'private'}, {osm_tags: {access: 'no'}}]) {
  const [limited] = Beta.places([{...shelter, properties: {...shelter.properties, ...properties}}]);
  assert.equal(limited.id, 'closed');
  assert.match(limited.evidenceNotice, /개방으로 가정/);
}
assert.equal(E.restStatus({...candidate, operation: 'closed'}).eligible, false);
assert.equal(E.restStatus(candidate).eligible, true);
assert.equal(Beta.nearbyRest(E, [candidate.ll], [candidate], {rest: true}).id, 'closed');
assert.equal(Beta.nearbyRest(E, [[35, 127]], [candidate], {rest: true}), null);
const start = [37.59, 127.039], end = [37.59, 127.041];
const closedOnly = E.createGraph({elements: [
  ...[start, candidate.ll, end].map(([lat, lon], i) => ({type: 'node', id: i + 1, lat, lon})),
  {type: 'way', id: 10, nodes: [1, 2, 3], tags: {highway: 'footway'}},
]});
const restProfile = {rest: true, restKind: 'shelter', speed: 60, atTime: '2026-11-22T17:00:00Z'};
closedOnly.restPlaces = [{...candidate, operation: 'closed'}];
assert.equal(Endpoint.route(E, closedOnly, start, end, restProfile).restStop, null);
assert.equal(Beta.localRoute(E, Endpoint, closedOnly, start, end, {...restProfile, restMinutes: 1}, [candidate]).restStop.id, 'closed');
const wheelchair = {wheelchair: true, avoidSteps: true, avoidSlope: true, maxSlope: 3, speed: 55};
const rampStart = [37.59, 127.037];
const ramp = E.createGraph({elements: [
  ...[rampStart, candidate.ll, end].map(([lat, lon], i) => ({type: 'node', id: i + 1, lat, lon})),
  {type: 'way', id: 11, nodes: [1, 2], tags: {highway: 'footway', incline: '8%'}},
  {type: 'way', id: 12, nodes: [2, 3], tags: {highway: 'footway'}},
]});
const missing = Beta.localRoute(E, Endpoint, closedOnly, start, end, wheelchair, []);
assert(!missing.demoSlopeRelaxed && missing.unknown > 0 && missing.maxKnownSlope === null);
const relaxed = Beta.localRoute(E, Endpoint, ramp, rampStart, end, wheelchair, []);
assert(relaxed.demoSlopeRelaxed && relaxed.unknown > 0 && relaxed.maxKnownSlope === 8);
const rejectedSteps = {...ramp, nodes: new Map([...ramp.nodes].map(([id,node]) =>
  [id, {...node, edges: node.edges.map(edge => ({...edge, steps: true}))}]))};
assert.throws(() => Beta.localRoute(E, Endpoint, rejectedSteps, rampStart, end, wheelchair, []));
const input = {origin:start, destination:end, profile:Beta.cityProfile(wheelchair,true)};
assert.throws(() => walkingInput(input), error => error.code === 'invalid_profile');
const fallbackProfile = walkingInput(input,{allowDemoSlopeFallback:true}).profile;
assert(fallbackProfile.wheelchair && fallbackProfile.avoidSteps);
assert.equal(fallbackProfile.maxSlope, null);

const server = createApp({});
await new Promise(resolve => server.listen(0, '127.0.0.1', resolve));
const origin = 'http://127.0.0.1:' + server.address().port;
const portable = process.argv.includes('--bundle');
let browser;

try {
  browser = await chromium.launch({headless: true, executablePath: process.env.CHROME_PATH, args: ['--no-sandbox']});
  const page = await browser.newPage({viewport: {width: 393, height: 852}, hasTouch: true});
  const errors = [], requests = [];
  page.on('pageerror', error => errors.push(error.message));
  page.on('request', request => {
    if (request.url().startsWith(origin + '/api/')) requests.push({url: request.url(), body: request.postDataJSON()});
  });
  await page.route('https://**', route => route.abort());
  await page.goto(origin + (portable ? '/동행길-최종.html' : '/'));
  await page.waitForFunction(() => !document.querySelector('#find-route').disabled, null, {timeout: 60000});
  assert.match(await page.title(), /시연 베타/);
  await page.getByRole('button', {name: '더보기', exact: true}).click();
  await page.getByRole('button', {name: '월곡 오프라인 예시', exact: true}).click();
  await page.getByRole('heading', {name: '베타 시연 경로', exact: true}).first().waitFor();
  const demo = await page.evaluate(() => ({
    route: routes[0]?.coords.length, sampleRest: routes[0]?.restStop?.name, selected,
    evidenceIgnored: routes[0]?.demoNotes.some(note => note.includes('운영시간')),
    canSave: !document.querySelector('#mobile-save').hidden,
    selectionIneligible: routes[0]?.selectionIneligible,
  }));
  assert(demo.route > 1 && demo.sampleRest);
  assert.equal(demo.selected, 0);
  assert.equal(demo.evidenceIgnored, true);
  assert.equal(demo.canSave, false);
  assert.equal(demo.selectionIneligible, true);
  await page.evaluate(() => startNavigation(false));
  assert.equal(await page.locator('#navigation-panel').getAttribute('hidden'), '');
  await page.getByRole('button', {name: '경로 모의 재생', exact: true}).click();
  assert.equal(await page.evaluate(() => navigationSession.snapshot().mode), 'replay');
  assert.deepEqual(requests, []);
  await page.evaluate(() => endNavigation());

  const runCity = (condition = '무더위쉼터에서 쉬고 싶어요.') => page.evaluate(condition => {
    setOrigin([37.49809, 127.02764], '강남역 시연 출발');
    setDestination({ll: [37.5045, 127.04907], name: '서울 시연 도착'});
    setCondition(condition);
    document.querySelector('#search').requestSubmit();
  }, condition);
  await runCity();
  await page.getByRole('heading', {name: '서울 베타 시연 경로', exact: true}).waitFor({timeout: 25000});
  const city = requests.find(({url}) => url.endsWith('/api/routes/city-walk'));
  assert.equal(city?.body.profile.rest, false);
  assert(await page.locator('#routes .demo-beta-rest').isVisible());
  const cityUrl = '**/api/routes/city-walk';
  const actualCityResponse = await page.request.post(origin + '/api/routes/city-walk', {data: city.body});
  const actualRoute = await actualCityResponse.json();
  const attempted = [];
  await page.route(cityUrl, route => {
    const {profile} = route.request().postDataJSON();
    attempted.push(profile);
    return profile.demoIgnoreSlope
      ? route.fulfill({status:200,json:{...actualRoute,registeredInclineMax:6,unknownInclineMeters:123}})
      : route.fulfill({status:422,json:{code:'city_no_connected_route',error:'모의 경사 자료 부족'}});
  });
  await runCity('휠체어를 이용해요. 계단을 피하고 경사 3% 이내로 가고 싶어요.');
  await page.locator('#routes .demo-beta-slope', {hasText:'경사 제한 없이'}).waitFor();
  assert.equal(attempted.length,2);
  assert.equal(attempted[0].maxSlope,3);
  assert.equal(attempted[1].maxSlope,null);
  assert(attempted[1].wheelchair && attempted[1].avoidSteps && attempted[1].demoIgnoreSlope);
  assert.match(await page.locator('#routes').innerText(), /6\.0%/);
  assert.match(await page.locator('#routes').innerText(), /경사 미확인 123m/);
  await page.unroute(cityUrl);

  await page.route('**/api/routes/city-walk', route => route.fulfill({status: 503, json: {error: '모의 연결 실패'}}));
  await runCity();
  await page.getByRole('heading', {name: '시연 예시를 실행할 수 있어요'}).waitFor();
  await page.locator('#routes').getByRole('button', {name: '월곡 오프라인 예시 실행'}).click();
  await page.getByRole('button', {name: '경로 모의 재생', exact: true}).waitFor();
  await page.evaluate(() => mapLayers.open(3));
  await page.getByText('오스코 주변 지형 경사 참고', {exact:true}).click();
  const terrain = page.locator('.osco-panel details', {hasText:'오스코 주변 지형 경사 참고'});
  assert.match(await terrain.innerText(), /2022년 5m 표고모형/);
  assert.match(await terrain.innerText(), /오송역 8번 출구 · 5도 미만/);
  assert.match(await terrain.innerText(), /보도 노면 실측.*미확인/);
  assert.deepEqual(errors, []);
  console.log(JSON.stringify({pass: true, entry: portable ? 'single-html' : 'main-source',
    closedShelterIncluded: true, offlineSample: demo.sampleRest, cityRouteAndFailureFallback: true, realGps: false}));
} finally {
  await browser?.close();
  server.closeAllConnections();
  await new Promise(resolve => server.close(resolve));
}
