import assert from 'node:assert/strict';
import {createRequire} from 'node:module';
import {createApp} from '../server.mjs';

const require = createRequire(import.meta.url);
const {chromium} = require('playwright');
const server = createApp({});
await new Promise(resolve => server.listen(0, '127.0.0.1', resolve));
const url = 'http://127.0.0.1:' + server.address().port;
const portable = process.argv.includes('--bundle');
let browser;

try {
  browser = await chromium.launch({headless: true, executablePath: process.env.CHROME_PATH, args: ['--no-sandbox']});
  const page = await browser.newPage({viewport: {width: 393, height: 852}, hasTouch: true});
  const errors = [];
  page.on('pageerror', error => errors.push(error.message));
  await page.route('https://**', route => route.abort());
  const asset = '**/seoul-rest-update.json.gz';
  if (!portable) await page.route(asset, route => route.fulfill({status: 503}));
  await page.goto(url + (portable ? '/동행길-최종.html' : '/'));
  await page.waitForFunction(() => !document.querySelector('#find-route').disabled, null, {timeout: 60000});
  const restState = state => page.waitForFunction(expected =>
    document.querySelector('.facility-control')?.dataset.restLoadState === expected, state);
  if (!portable) {
    await restState('error');
    assert.equal(await page.evaluate(() => graph.restPlaces.length), 229);
    await page.locator('.map-layers-control > summary').click();
    await page.unroute(asset);
    await page.getByRole('button', {name: '휴식 자료 다시 불러오기'}).click();
  }
  await restState('ready');

  const snapshot = await page.evaluate(() => ({
    official: facilityController.getMapFeatures().filter(f => f.properties.official_fields?.시설년도 === '2026').length,
    originalMapInput: facilityController.getFeatures().length,
    displayOnly: facilityController.getMapFeatures().filter(f => f.properties.routing_eligible === false).length,
    libraries: facilityController.getSnapshot().counts.library,
    libraryDestinations: cityDestinations.filter(f => String(f.id).startsWith('city-facility:library:')).length,
    restPlaces: graph.restPlaces.length,
    extraRestUsed: graph.restPlaces.some(f => f.kind === 'library' || f.id.startsWith('library:')),
  }));
  assert.deepEqual(snapshot, {
    official: 4092, originalMapInput: 17485, displayOnly: 4934, libraries: 214,
    libraryDestinations: 214, restPlaces: 229, extraRestUsed: false,
  });
  if (portable) await page.locator('.map-layers-control > summary').click();
  const directory = page.locator('.facility-directory');
  await directory.locator(':scope > summary').click();
  await directory.getByRole('searchbox').fill('웰빙스포츠센터');
  assert.equal(await directory.locator('.facility-directory-entry').count(), 1);
  await directory.getByText('강북웰빙스포츠센터', {exact: true}).click();
  assert.match(await directory.innerText(), /지도 좌표 미제공/);
  assert.match(await directory.innerText(), /토요일 09:00~17:00/);
  assert.match(await directory.innerText(), /09:00~18:00/);
  assert.equal(await directory.getByRole('button', {name: '이 장소로 길 찾기'}).count(), 0);

  const search = page.getByRole('searchbox', {name: '서울 시설 이름 또는 주소 검색'});
  await search.fill('가락몰도서관');
  await page.getByRole('button', {name: '공공도서관 · 가락몰도서관', exact: true}).click();
  const popup = page.locator('.facility-popup');
  await popup.waitFor();
  assert.match(await popup.innerText(), /국가도서관통계시스템/);
  assert.match(await popup.innerText(), /정기 휴관일/);
  assert.match(await popup.innerText(), /현재 이용 가능 여부 미확인/);
  await popup.getByRole('button', {name: '이 장소로 길 찾기 →', exact: true}).click();
  assert.equal(await page.locator('#destination-query').inputValue(), '가락몰도서관');
  assert.deepEqual(errors, []);
  console.log(JSON.stringify({pass: true, entry: portable ? 'single-html' : 'main-source', snapshot}));
} finally {
  await browser?.close();
  server.closeAllConnections();
  await new Promise(resolve => server.close(resolve));
}
