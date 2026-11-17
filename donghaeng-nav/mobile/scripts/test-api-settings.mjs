import assert from 'node:assert/strict';
import {createServer} from 'node:http';
import {readFile, writeFile} from 'node:fs/promises';
import path from 'node:path';
import {createRequire} from 'node:module';
import {build} from 'esbuild';
const {chromium} = createRequire(import.meta.url)('playwright'), mobile = path.resolve('.');
const checks = [], errors = [], geminiRequests = [], backendRequests = [];
let deviceGemini = false, keySource = 'bundled', failure = null;
const profile = {wheelchair: false, avoidSteps: true, avoidSlope: false, rest: false, short: false, recognized: true, restMinutes: null, restKind: 'any', maxSlope: null};
const state = () => ({configured: keySource !== 'disabled', keySource, bundledKeyAvailable: true, geminiConfigured: deviceGemini, used: 0, dailyLimit: 20});
await build({entryPoints: ['src/runtime.js'], bundle: true, format: 'iife', platform: 'browser', target: 'chrome100', outfile: '/tmp/donghaeng-api-settings-test.js', plugins: [{name: 'native-doubles', setup(b) {
 b.onResolve({filter: /^@capacitor\/core$/}, () => ({path: 'core', namespace: 'test'}));
 b.onResolve({filter: /^@capacitor\/geolocation$/}, () => ({path: 'gps', namespace: 'test'}));
 b.onLoad({filter: /.*/, namespace: 'test'}, a => ({contents: a.path === 'core' ? 'export const registerPlugin=()=>globalThis.NativeTest;' : 'export const Geolocation={checkPermissions:async()=>({location:"granted"})};'}));
 b.onResolve({filter: /city-walk\/router\.mjs$/}, () => ({path: path.join(mobile, 'src/city-backend.js')}));
 b.onResolve({filter: /^node:crypto$/}, () => ({path: path.join(mobile, 'src/hash.js')}));
}}]});
const server = createServer(async (req, res) => {
 try {
  const pathname = new URL(req.url, 'http://localhost').pathname;
  const file = pathname === '/native-runtime.js' ? '/tmp/donghaeng-api-settings-test.js' : path.join(mobile, 'www', pathname === '/' ? 'index.html' : pathname);
  const raw = await readFile(file); res.setHeader('Content-Type', file.endsWith('.js') ? 'text/javascript' : file.endsWith('.css') ? 'text/css' : file.endsWith('.html') ? 'text/html' : 'application/octet-stream'); res.end(raw);
 } catch {res.statusCode = 404; res.end();}
});
await new Promise(r => server.listen(0, '127.0.0.1', r)); let browser;
try {
 browser = await chromium.launch({headless: true, executablePath: '/usr/bin/chromium', args: ['--no-sandbox']});
 const context = await browser.newContext({viewport: {width: 393, height: 852}}); await context.route('https://**', r => r.abort());
 const page = await context.newPage(); page.on('pageerror', e => errors.push(e.message));
 await page.exposeFunction('testStatus', state);
 await page.exposeFunction('testConfigureGemini', () => {deviceGemini = true; return {...state(), changed: true};});
 await page.exposeFunction('testClearGemini', () => {deviceGemini = false; return {...state(), changed: true};});
 await page.exposeFunction('testResetKey', () => {keySource = 'bundled'; return {...state(), changed: true};});
 await page.exposeFunction('testConfigureKey', () => {keySource = 'device'; return {...state(), changed: true};});
 await page.exposeFunction('testBackend', o => {
  backendRequests.push(o); return {status: 200, body: JSON.stringify(o.path === '/api/status' ? {configured: true, provider: 'Gemini', model: 'gemini-3.5-flash-lite'} : {profile, source: 'Gemini', keySource: 'server'})};
 });
 await page.exposeFunction('testGemini', o => {
  geminiRequests.push(o);
  if (failure === 'quota') return {status: 429, body: '{"code":"gemini_quota","error":"Gemini 사용 한도에 도달했어요."}'};
  if (failure === 'invalid') return {status: 200, body: '{"candidates":[]}'};
  const input = JSON.parse(o.request.contents[0].parts[0].text.startsWith('{') ? o.request.contents[0].parts[0].text : '{}');
  const decision = input.candidates ? {selectedId: input.candidates[0].id, summary: '등록 수치를 비교한 참고 선택', advantages: ['짧은 거리'], tradeoffs: ['노면 실측 없음'], cautions: ['출입구 미확인'], comparisons: input.candidates.map(c => ({id: c.id, comment: '거리와 미확인 수치 대조'}))} : null;
  return {status: 200, body: JSON.stringify({candidates: [{content: {parts: [{text: JSON.stringify(decision || profile)}]}}]})};
 });
 await page.addInitScript(() => {window.NativeTest = {status: () => window.testStatus(), backend: o => window.testBackend(o), gemini: o => window.testGemini(o), configureGemini: () => window.testConfigureGemini(), clearGemini: () => window.testClearGemini(), resetKey: () => window.testResetKey(), configureKey: () => window.testConfigureKey(), cancel: async () => ({})};});
 const base = 'http://127.0.0.1:' + server.address().port;
 await page.goto(base); await page.waitForFunction(() => !document.querySelector('#find-route').disabled, null, {timeout: 60000});
 await page.getByRole('button', {name: 'API 설정', exact: true}).click();
 await page.waitForFunction(() => document.querySelector('#android-gemini-key-state').textContent.includes('서버 Gemini 설정 있음'));
 assert.match(await page.locator('#android-traffic-key-state').innerText(), /내장 키 적용 중/);
 assert.equal(geminiRequests.length, 0);
 await page.getByRole('button', {name: 'Gemini API 키 입력·변경', exact: true}).click();
 await page.waitForFunction(() => document.querySelector('#android-gemini-key-state').textContent.includes('기기에 입력한'));
 await page.getByRole('button', {name: 'API 설정 닫기', exact: true}).click();
 const analyze = () => page.evaluate(async () => {const r = await fetch('/api/analyze-condition', {method: 'POST', headers: {'Content-Type': 'application/json'}, body: JSON.stringify({condition: '계단을 피해서 걷고 싶어요.'})}); return {status: r.status, data: await r.json()};});
 const before = backendRequests.filter(r => r.path === '/api/analyze-condition').length;
 const result = await analyze(); assert.equal(result.status, 200); assert.equal(result.data.keySource, 'android-device'); assert.equal(result.data.profile.avoidSteps, true);
 assert.equal(backendRequests.filter(r => r.path === '/api/analyze-condition').length, before);
 assert.equal(geminiRequests.length, 1); assert.equal(geminiRequests[0].request.contents[0].parts[0].text, '계단을 피해서 걷고 싶어요.');
 assert(!('apiKey' in geminiRequests[0])); assert(!('key' in geminiRequests[0]));
 checks.push('API settings clearly distinguishes bundled ODsay and server Gemini; configuring a device Gemini key routes validated condition-only requests through the native bridge with no key or coordinates in the JS payload.');
 const choice = await page.evaluate(async () => {
  const metrics = {distanceMeters: 1000, minutes: 20, maxReferenceSlope: null, above3Meters: 0, unknownMeters: 1000, unresolvedMeters: 0, stairsMeters: 0, roughMeters: 0, connectionMeters: 0, restFulfilled: true, fieldVerified: false};
  const input = {condition: '계단을 피하고 싶어요.', profile: {wheelchair: false, avoidSteps: true, avoidSlope: false, rest: false, short: false, maxSlope: null, restKind: 'any'}, candidates: [{id: 'R1', ...metrics}, {id: 'R2', ...metrics, distanceMeters: 1200}]};
  const r = await fetch('/api/select-route', {method: 'POST', body: JSON.stringify(input)}); return {status: r.status, data: await r.json()};
 });
 assert.equal(choice.status, 200); assert.equal(choice.data.decision.selectedId, 'R1');
 assert(!JSON.stringify(geminiRequests.at(-1).request).includes('coordinates'));
 const current = geminiRequests.length;
 const invalid = await page.evaluate(async () => {const r = await fetch('/api/analyze-condition', {method: 'POST', body: JSON.stringify({condition: '시험', coordinates: [127, 37]})}); return r.status;});
 assert.equal(invalid, 400); assert.equal(geminiRequests.length, current);
 failure = 'quota'; assert.equal((await analyze()).status, 429); failure = 'invalid'; assert.equal((await analyze()).status, 502); failure = null;
 assert.equal(backendRequests.filter(r => r.path === '/api/analyze-condition').length, before);
 checks.push('Anonymous candidate comparison uses the existing validators; extra coordinate fields are rejected before Google, quota and malformed responses fail honestly without an automatic paid server retry.');
 await page.reload(); await page.waitForFunction(() => !document.querySelector('#find-route').disabled, null, {timeout: 60000});
 await page.getByRole('button', {name: 'API 설정', exact: true}).click();
 await page.waitForFunction(() => document.querySelector('#android-gemini-key-state').textContent.includes('기기에 입력한'));
 for (const size of [{width: 320, height: 568}, {width: 393, height: 852}, {width: 667, height: 375}]) {await page.setViewportSize(size); assert(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth));}
 await page.setViewportSize({width: 393, height: 852}); await page.screenshot({path: '../docs/android-api-settings-mobile.png'});
 await page.getByRole('button', {name: 'Gemini 기기 키 삭제 · 서버 사용', exact: true}).click();
 await page.waitForFunction(() => document.querySelector('#android-gemini-key-state').textContent.includes('서버 Gemini 설정 있음'));
 keySource = 'disabled'; await page.getByRole('button', {name: '대중교통 내장 키 복원', exact: true}).click();
 await page.waitForFunction(() => document.querySelector('#android-traffic-key-state').textContent.includes('내장 키 적용 중'));
 await page.getByRole('button', {name: 'API 설정 닫기', exact: true}).click();
 const googleBefore = geminiRequests.length; assert.equal((await analyze()).data.keySource, 'server'); assert.equal(geminiRequests.length, googleBefore);
 checks.push('Saved native-state mock survives page restart; Gemini deletion returns to server mode, disabled ODsay can restore the embedded default, and the settings dialog fits small/landscape screens.');
 assert.deepEqual(errors, []);
 const report = {pass: true, checks, browserErrors: errors, nativeBridgeMocked: true, actualGoogleCalls: 0, actualOdsayCalls: 0, realGeminiKeyInTests: false, actualAndroidDeviceTest: false, fieldVerified: false};
 await writeFile('../docs/android-api-settings-results.json', JSON.stringify(report, null, 2) + '\n'); console.log(JSON.stringify(report, null, 2));
} finally {await browser?.close(); server.closeAllConnections(); await new Promise(r => server.close(r));}
