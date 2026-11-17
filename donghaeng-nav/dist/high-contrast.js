(function (root) {
 'use strict';
 const doc = document, key = 'donghaeng.display.contrast';
 const preference = root.matchMedia?.('(prefers-contrast: more)');
 const values = new Set(['high', 'standard']);
 let choice = null, announcement;
 try { const saved = root.localStorage.getItem(key); if (values.has(saved)) choice = saved; } catch {}
 const active = () => doc.documentElement.dataset.contrast === 'high';
 function apply() {
  const high = choice === 'high' || (choice === null && preference?.matches === true);
  doc.documentElement.dataset.contrast = high ? 'high' : 'standard';
  doc.querySelectorAll('[data-contrast-toggle]').forEach(button => {
   button.setAttribute('aria-pressed', String(high));
   button.textContent = high ? '◐ 밤하늘' : '◐ 고대비';
   button.title = '고대비 · 밤하늘 테마';
  });
  doc.dispatchEvent(new CustomEvent('donghaeng-contrast-change', {detail: {high}}));
  return high;
 }
 function set(high) {
  choice = high ? 'high' : 'standard';
  let saved = true;
  try { root.localStorage.setItem(key, choice); } catch { saved = false; }
  apply();
  if (announcement) announcement.textContent = (high ? '고대비 모드를 켰습니다.' : '기본 화면으로 바꿨습니다.') +
   (saved ? '' : ' 설정을 저장하지 못해 이 창에서만 적용합니다.');
 }
 const styles = {
  route: {color: '#003fbd', dashArray: null, weight: 7},
  alternative: {color: '#111111', dashArray: '16 9', weight: 5},
  'registered-risk': {color: '#111111', dashArray: '5 3', weight: 9},
  'estimated-risk': {color: '#111111', dashArray: '13 7', weight: 9},
  unverified: {color: '#111111', dashArray: '2 8', weight: 8, lineCap: 'round'},
  steep: {color: '#111111', dashArray: '14 5 3 5', weight: 5},
  context: {color: '#111111', dashArray: '6 4', weight: 2.5},
  building: {color: '#111111', fillColor: '#ffffff', weight: 2},
  position: {color: '#111111', fillColor: '#0052cc', weight: 3},
  accuracy: {color: '#111111', dashArray: '4 5', weight: 2},
  progress: {color: '#111111', dashArray: '2 5', weight: 7},
  stage: {color: '#111111', dashArray: '14 5 3 5', weight: 9},
  simulation: {color: '#111111', fillColor: '#ffffff', weight: 3},
 };
 function bindMap(map) {
  const originals = new WeakMap(), layers = new Set();
  function restyle(layer) {
   const role = layer.options?.contrastRole, style = styles[role];
   if (!style || typeof layer.setStyle !== 'function') return;
   if (!originals.has(layer)) originals.set(layer, Object.fromEntries(Object.keys(style).map(k => [k, layer.options[k]])));
   layer.setStyle(active() ? style : originals.get(layer));
  }
  const add = e => {layers.add(e.layer); restyle(e.layer);};
  const remove = e => layers.delete(e.layer);
  const update = () => layers.forEach(restyle);
  map.eachLayer(layer => add({layer}));
  map.on('layeradd', add); map.on('layerremove', remove);
  doc.addEventListener('donghaeng-contrast-change', update);
  map.once('unload', () => {
   map.off('layeradd', add); map.off('layerremove', remove);
   doc.removeEventListener('donghaeng-contrast-change', update); layers.clear();
  });
 }
 function legend() {
  const box = doc.createElement('details'); box.className = 'contrast-legend';
  const title = doc.createElement('summary'); title.textContent = '고대비 지도 범례'; box.append(title);
  for (const [kind, text] of [['route', '선택 경로 · 굵은 실선'], ['alternative', '다른 경로 · 긴 파선'],
   ['registered-risk', '등록 경사 주의 · 짧은 파선'], ['estimated-risk', '추정·자료 차이 · 긴 파선'],
   ['unverified', '구조물·접속 미확인 · 점선'], ['steep', '급경사 참고 자료 · 일점쇄선']]) {
   const line = doc.createElement('p'), sample = doc.createElement('span');
   sample.className = 'contrast-sample contrast-' + kind; sample.setAttribute('aria-hidden', 'true');
   line.append(sample, doc.createTextNode(text)); box.append(line);
  }
  box.append(doc.createTextNode('선 모양은 표시 구분입니다. 현장 안전이나 통행 확인을 뜻하지 않습니다.'));
  return box;
 }
 apply();
 preference?.addEventListener?.('change', () => {if (choice === null) apply();});
 root.addEventListener('storage', event => {
  if (event.key !== key && event.key !== null) return;
  choice = values.has(event.newValue) ? event.newValue : null; apply();
 });
 function ready() {
  announcement = doc.createElement('p'); announcement.className = 'contrast-announcement';
  announcement.role = 'status'; announcement.setAttribute('aria-live', 'polite');
  doc.body.append(announcement);
  doc.querySelectorAll('[data-contrast-toggle]').forEach(button => button.addEventListener('click', () => set(!active())));
  apply();
 }
 if (doc.readyState === 'loading') doc.addEventListener('DOMContentLoaded', ready, {once: true}); else ready();
 root.HighContrast = {active, set, bindMap, legend};
})(globalThis);
