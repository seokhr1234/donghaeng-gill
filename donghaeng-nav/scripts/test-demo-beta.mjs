import assert from 'node:assert/strict';
import {createRequire} from 'node:module';
import {createApp} from '../server.mjs';

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

  const runCity = () => page.evaluate(() => {
    setOrigin([37.49809, 127.02764], '강남역 시연 출발');
    setDestination({ll: [37.5045, 127.04907], name: '서울 시연 도착'});
    setCondition('무더위쉼터에서 쉬고 싶어요.');
    document.querySelector('#search').requestSubmit();
  });
  await runCity();
  await page.getByRole('heading', {name: '서울 베타 시연 경로', exact: true}).waitFor({timeout: 25000});
  const city = requests.find(({url}) => url.endsWith('/api/routes/city-walk'));
  assert.equal(city?.body.profile.rest, false);
  assert(await page.locator('#routes .demo-beta-rest').isVisible());

  await page.route('**/api/routes/city-walk', route => route.fulfill({status: 503, json: {error: '모의 연결 실패'}}));
  await runCity();
  await page.getByRole('heading', {name: '시연 예시를 실행할 수 있어요'}).waitFor();
  await page.locator('#routes').getByRole('button', {name: '월곡 오프라인 예시 실행'}).click();
  await page.getByRole('button', {name: '경로 모의 재생', exact: true}).waitFor();
  assert.deepEqual(errors, []);
  console.log(JSON.stringify({pass: true, entry: portable ? 'single-html' : 'main-source',
    closedShelterIncluded: true, offlineSample: demo.sampleRest, cityRouteAndFailureFallback: true, realGps: false}));
} finally {
  await browser?.close();
  server.closeAllConnections();
  await new Promise(resolve => server.close(resolve));
}
