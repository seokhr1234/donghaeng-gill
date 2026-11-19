(function (root) {
 'use strict';
 const AREA = [127.28, 36.59, 127.39, 36.67];
 function inScope(ll) {
  return Array.isArray(ll) && ll.length === 2 && ll.every(Number.isFinite) &&
   ll[1] >= AREA[0] && ll[1] <= AREA[2] && ll[0] >= AREA[1] && ll[0] <= AREA[3];
 }
 function info() {
  const data = JSON.parse(document.getElementById('bundled-osco-info').textContent);
  if (data.schema !== 'donghaeng-osco-info-v1' || data.display_only !== true ||
      data.field_verified !== false || data.routing_eligible !== false) throw Error('오스코 출처 자료를 확인하지 못했어요.');
  return data;
 }
 function places() { return info().places; }
 const el = (tag, text, cls) => {
  const e = document.createElement(tag);
  if (text !== undefined) e.textContent = text;
  if (cls) e.className = cls;
  return e;
 };
 function link(text, url) {
  const a = el('a', text);
  try {
   const u = new URL(url);
   if (!['https:', 'http:'].includes(u.protocol)) return el('span', text);
   a.href = u.href; a.target = '_blank'; a.rel = 'noopener noreferrer';
  } catch { return el('span', text); }
  return a;
 }
 function sourceLine(source) {
  const p = el('p', undefined, 'osco-source');
  p.append(link(source.id, source.url), el('small', '수집 ' + source.requested_at_kst +
   ' · 자료 기준 ' + (source.source_as_of || '미확인') +
   (source.page_modified_at ? ' · 페이지 수정 ' + source.page_modified_at + ' (실측일 아님)' : '')));
  return p;
 }
 function create(map, {fitBounds, onSelectOrigin, onSelectDestination} = {}) {
  const L = root.L, data = info(), panel = el('section', undefined, 'osco-panel');
  panel.setAttribute('aria-label', '청주오스코 조사 지도');
  panel.append(el('h3', '청주오스코 주변'), el('p', 'OSM 등록 지물과 공식 안내를 함께 확인해요. 현장 통행·출입구는 미확인입니다.', 'osco-note'));
  const buttons = el('div', undefined, 'osco-actions');
  const source = id => data.sources.find(s => s.id === id);
  const markers = L.layerGroup().addTo(map), layers = L.featureGroup().addTo(map);
  const venueMarkers = new Map(), checkboxes = {}, counts = {};
  let context = null, loading = false, failed = false, disposed = false, rendered = 0;
  const status = el('p', '', 'osco-layer-status'); status.role = 'status';
  // The shared loader caches parsed text. Preserve its original source block so
  // a rejected schema can be fetched again instead of retrying poisoned text.
  const contextTemplate = document.getElementById('bundled-osco-context').cloneNode(true);
  const retry = el('button', '자료 다시 불러오기'); retry.type = 'button'; retry.hidden = true;
  const kinds = [
   ['roads', '등록 보행로·계단', 16], ['access_points', '횡단·출입 등록', 17],
   ['transport', '정류장·철도 등록', 16], ['facilities', '휴식·화장실·주차 등록', 17],
   ['buildings', '건물 윤곽', 17],
  ];
  function selectButtons(place, box) {
   const actions = el('div', undefined, 'osco-actions');
   for (const [text, callback] of [['출발지로 선택', onSelectOrigin], ['목적지로 선택', onSelectDestination]]) {
    const b = el('button', text); b.type = 'button';
    b.onclick = () => { map.closePopup(); callback?.(place); };
    actions.append(b);
   }
   box.append(actions, el('p', root.DONGHAENG_BUILD?.transitEnabled ?
    '대표점 기준 선택 · Android 대중교통 참고 검색에 사용할 수 있어요. 출입구·도보 연계는 미확인입니다.' :
    '청주 주변은 자료 표시를 제공합니다. 도보 경로 계산은 서울 범위에서 사용할 수 있어요.', 'osco-note'));
  }
  function venuePopup(place) {
   const box = el('section', undefined, 'osco-popup osco-venue-detail');
   box.append(el('h3', place.name), el('p', place.address),
    el('p', (place.id === 'osco:venue' ? '공식 안내의 대표점' : 'OSM 등록 대표점') + ' · 실제 보행 출입구 아님', 'osco-warning'));
   if (place.id === 'osco:venue') {
    const bf = data.bf_certificate, parking = data.parking_claims;
    box.append(el('p', 'BF 본인증 ' + bf.grade + ' · ' + bf.certificate_number + '호'),
     el('p', bf.issued + ' ~ ' + bf.reported_expiry + ' · 등록명 ' + bf.registered_facility_name),
     el('p', '건물 인증이며 오송역부터의 접근로·당일 운영 확인은 별도입니다.', 'osco-note'),
     link('BF 공식 인증 상세', source('bf-osco-detail-main').url),
     el('p', '공식 주차 안내 ' + parking.operator_parking_plan_total + '대 / 시설 가이드 ' + parking.facility_pdf_overview_total + '대 · 표기 차이 있음', 'osco-warning'),
     el('p', '주차 도면의 장애인 50대는 총수에 포함 · 현재 빈자리·무단차 접근 미확인'),
     link('공식 주차 안내', source('osco-parking').url),
     el('p', '시설 가이드에 승강기·장애인화장실·수유실·의무지원실이 표시돼 있어요. 도면과 실제 시설은 다를 수 있습니다.'),
     link('공식 시설 가이드 · 34쪽 PDF', source('osco-facility-pdf').url));
   } else {
    box.append(el('p', 'OSM 철도역 대표 위치 · 철도역 8번 출입구와 버스정류장 ‘오송역8’은 별개입니다.'),
     link('OSM 등록 원문', place.sourceUrl));
   }
   const details = el('details'); details.append(el('summary', '출처·자료 기준·수집일'));
   for (const id of place.id === 'osco:venue' ? ['gallery-directions', 'bf-osco-detail-main', 'osco-parking', 'osco-facility-pdf'] : ['geofabrik-korea-261115-pbf']) details.append(sourceLine(source(id)));
   details.append(el('p', '현장 확인: 미실시 · 대표점 좌표 EPSG:4326 · 내부 도면 좌표계 미확인', 'osco-note'));
   box.append(details); selectButtons(place, box); return box;
  }
  function showPlace(place, popup = true) {
   map.stop().setView(place.ll, 17, {animate: false}); render();
   if (popup) venueMarkers.get(place.id)?.openPopup();
  }
  for (const place of data.places) {
   const b = el('button', place.id === 'osco:venue' ? '행사장·공식 안내' : '오송역 보기'); b.type = 'button';
   b.onclick = () => showPlace(place); buttons.append(b);
   const marker = L.marker(place.ll, {title: place.name, icon: L.divIcon({className: 'osco-pin',
    html: '<span>' + (place.id === 'osco:venue' ? '오스코' : '오송역') + '</span>', iconSize: [60, 30], iconAnchor: [30, 30]})});
   marker.bindPopup(() => venuePopup(place), {maxWidth: 330, maxHeight: 360, autoPanPaddingTopLeft: [12, 20], autoPanPaddingBottomRight: [12, 84]});
   venueMarkers.set(place.id, marker);
  }
  panel.append(buttons);
  for (const [kind, title] of kinds) {
   const label = el('label', undefined, 'osco-toggle'), c = el('input'); c.type = 'checkbox'; c.id = 'osco-' + kind;
   c.onchange = () => { if (c.checked && !context) load(); else render(); };
   label.append(c, document.createTextNode(title)); panel.append(label); checkboxes[kind] = c;
  }
  panel.append(status, retry, el('p', '확대 후 현재 화면의 지물만 표시해요. 건수는 등록 객체 수이며 실제 시설 수와 다를 수 있어요.', 'osco-note'));
  const evidence = el('details'); evidence.append(el('summary', '조사 출처와 적용 범위'));
  evidence.append(el('p', 'OSM 자료 기준 ' + data.osm_source_metadata.source_as_of + ' · EPSG:4326 · ODbL-1.0'),
   el('p', data.terrain_notice), el('p', '청주시 상세 도형과 가공 쉼터·화장실은 재이용 조건을 확인 중이라 표시에서 보류했습니다.'),
   link('© OpenStreetMap contributors · ODbL', 'https://www.openstreetmap.org/copyright'));
  for (const s of data.sources) evidence.append(sourceLine(s));
  panel.append(evidence);
  function eligible(kind, f) {
   const t = f.properties.tags || {};
   if (kind === 'roads') return ['footway', 'path', 'pedestrian', 'steps'].includes(t.highway);
   if (kind === 'transport') return f.geometry.type === 'Point' &&
    (t.highway === 'bus_stop' || t.public_transport === 'platform' || t.public_transport === 'station' || t.railway === 'station');
   if (kind === 'facilities') return ['bench', 'toilets', 'parking', 'shelter', 'drinking_water'].includes(t.amenity) || t.highway === 'rest_area';
   return true;
  }
  function bounds(geometry) {
   const out = [Infinity, Infinity, -Infinity, -Infinity];
   function visit(c) {
    if (typeof c[0] === 'number') {out[0] = Math.min(out[0], c[0]); out[1] = Math.min(out[1], c[1]); out[2] = Math.max(out[2], c[0]); out[3] = Math.max(out[3], c[1]);}
    else c.forEach(visit);
   }
   visit(geometry.coordinates); return out;
  }
  async function load() {
   if (context || loading || disposed) return;
   loading = true; failed = false; render();
   try {
    const raw = JSON.parse(await root.DONGHAENG_LOAD_DATA('bundled-osco-context'));
    if (raw.schema !== 'donghaeng-osco-context-v1' || raw.display_only !== true || raw.field_verified !== false || raw.routing_eligible !== false) throw Error('오스코 도형 형식 오류');
    const prepared = {};
    for (const [kind] of kinds) {
     if (!Array.isArray(raw.layers?.[kind]) || raw.layers[kind].length !== data.osm_layer_counts[kind]) throw Error('오스코 도형 수 불일치');
     prepared[kind] = raw.layers[kind].filter(f => eligible(kind, f)).map(f => ({feature: f, bounds: bounds(f.geometry)}));
    }
    context = prepared;
   } catch {
    failed = true;
    document.getElementById('bundled-osco-context').replaceWith(contextTemplate.cloneNode(true));
   }
   finally { loading = false; render(); }
  }
  function featurePopup(f, kind) {
   const p = f.properties, t = p.tags || {}, box = el('section', undefined, 'osco-popup');
   box.append(el('h3', t.name || kinds.find(k => k[0] === kind)[1]), el('p', 'OSM 등록 · 현장 미확인', 'osco-warning'));
   const dl = el('dl');
   for (const [key, title] of [['highway', '도로 종류'], ['amenity', '시설 종류'], ['public_transport', '교통 등록'],
    ['crossing', '횡단 등록'], ['entrance', '출입 등록'], ['wheelchair', '휠체어 표기'], ['tactile_paving', '점자블록 표기'],
    ['kerb', '턱 표기'], ['width', '폭 원문'], ['incline', '경사 원문'], ['access', '출입 표기'], ['opening_hours', '운영시간 표기']]) {
    if (t[key] !== undefined) dl.append(el('dt', title), el('dd', String(t[key])));
   }
   dl.append(el('dt', '객체 갱신'), el('dd', p.osm_timestamp || '미확인'), el('dt', '자료 기준'), el('dd', data.osm_source_metadata.source_as_of),
    el('dt', '수집'), el('dd', source('geofabrik-korea-261115-pbf').requested_at_kst), el('dt', '좌표계'), el('dd', 'EPSG:4326'));
   box.append(dl, el('p', '표기는 등록 원문입니다. 빠진 값은 미확인이며 통행·턱·유효폭·운영을 확인한 것이 아닙니다.'),
    link('OSM 원문 · ' + f.id, 'https://www.openstreetmap.org/' + f.id));
   return box;
  }
  function render() {
   if (disposed) return;
   const center = map.getCenter(), areaLabel = document.getElementById('map-area-label');
   if (areaLabel) areaLabel.textContent = inScope([center.lat, center.lng]) ? '오스코 주변' : root.CityMap.inScope([center.lat, center.lng]) ? '서울 지도' : '지도';
   const b = map.getBounds(), zoom = map.getZoom(), selectedKinds = kinds.filter(([k]) => checkboxes[k].checked);
   for (const [id, m] of venueMarkers) {
    if (zoom >= 12 && b.pad(.1).contains(m.getLatLng())) { if (!markers.hasLayer(m)) markers.addLayer(m); }
    else if (!m.isPopupOpen()) markers.removeLayer(m);
   }
   // Auto-pan must not rebuild the marker whose details are being read.
   if (contextPopup) return;
   layers.clearLayers(); rendered = 0;
   let overflow = false, zoomHidden = false;
   const symbolGroups = new Map();
   const symbolFor = (feature, kind) => {
    const t = feature.properties.tags || {};
    return kind === 'transport' ? (t.railway === 'station' ? '역' : '정') :
     kind === 'access_points' ? (t.highway === 'crossing' ? '횡' : t.entrance ? '입' : t.barrier === 'kerb' ? '턱' : '접') :
     ({bench: '의', toilets: '화', parking: 'P', shelter: '쉼', drinking_water: '물'}[t.amenity] || '시');
   };
   for (const [kind, , minZoom] of selectedKinds) {
    counts[kind] = 0;
    if (zoom < minZoom) {zoomHidden = true; continue;}
    for (const {feature: f, bounds: box} of context?.[kind] || []) {
     if (box[0] > b.getEast() || box[2] < b.getWest() || box[1] > b.getNorth() || box[3] < b.getSouth()) continue;
     if (rendered >= 600) {overflow = true; break;}
     if (root.HighContrast?.active() && f.geometry.type === 'Point') {
      const c = f.geometry.coordinates, ll = [c[1], c[0]], pixel = map.latLngToContainerPoint(ll);
      const key = kind + ':' + Math.floor(pixel.x / 32) + ':' + Math.floor(pixel.y / 32);
      if (!symbolGroups.has(key)) symbolGroups.set(key, {kind, ll, features: []});
      symbolGroups.get(key).features.push(f); rendered++; counts[kind]++; continue;
     }
     const color = {roads: '#487b72', buildings: '#858b88', access_points: '#aa6431', transport: '#31678b', facilities: '#387e50'}[kind];
     L.geoJSON(f, {style: {contrastRole: kind === 'buildings' ? 'building' : 'context', color, weight: kind === 'buildings' ? 1 : 2, opacity: .65, fillOpacity: kind === 'buildings' ? .06 : .12},
      pointToLayer: (feature, ll) => L.circleMarker(ll, {radius: 5, color: '#fff', weight: 1.5, fillColor: color, fillOpacity: .9}),
      onEachFeature: (feature, layer) => layer.bindPopup(() => featurePopup(feature, kind), {maxWidth: 320, maxHeight: 300}),
     }).addTo(layers); rendered++; counts[kind]++;
    }
   }
   for (const group of symbolGroups.values()) {
    const {features, ll, kind} = group, symbol = features.length > 1 ? String(features.length) : symbolFor(features[0], kind);
    L.marker(ll, {title: kinds.find(k => k[0] === kind)[1] + ' · ' + features.length + '건 · 현장 미확인', icon: L.divIcon({
     className: 'hc-osco-marker hc-osco-' + kind + (features.length > 1 ? ' hc-osco-count' : ''), html: '<span>' + symbol + '</span>', iconSize: [24, 24], iconAnchor: [12, 12],
    })}).bindPopup(() => {
     if (features.length === 1) return featurePopup(features[0], kind);
     const box = el('section', undefined, 'osco-popup');
     box.append(el('h3', '가까운 등록 지점 ' + features.length + '건'), el('p', '화면상 겹침을 묶었습니다. 표시는 첫 원본 지점의 좌표이며 실제 한 시설이라는 뜻이 아닙니다.'));
     for (const f of features.slice(0, 10)) {const d = el('details'); d.append(el('summary', f.properties.tags?.name || f.id), featurePopup(f, kind)); box.append(d);}
     if (features.length > 10) box.append(el('p', '첫 10건을 표시합니다. 지도를 확대하면 나눠 볼 수 있어요.'));
     return box;
    }, {maxWidth: 320, maxHeight: 300}).addTo(layers);
   }
   retry.hidden = !failed || !selectedKinds.length;
   status.textContent = !selectedKinds.length ? '표시할 자료를 선택해 주세요.' : loading ? '오스코 등록 자료를 불러오는 중…' :
    failed ? '오스코 자료를 불러오지 못했어요. 다시 시도해 주세요.' :
    overflow ? '화면당 600개까지 표시해요. 확대하거나 표시 항목을 줄여 주세요.' :
    zoomHidden ? '일부 자료는 16~17단계 이상 확대하면 표시돼요.' :
    rendered ? '현재 화면의 등록 객체 ' + rendered + '개 · 현장 미확인' : '이 화면에 표시할 등록 자료가 없어요. 미등록 시설이 있을 수 있어요.';
  }
  let contextPopup = null;
  layers.on('popupopen', event => {contextPopup = event.popup;});
  layers.on('popupclose', event => {
   if (contextPopup === event.popup) contextPopup = null;
   requestAnimationFrame(render);
  });
  retry.onclick = load; map.on('moveend', render); document.addEventListener('donghaeng-contrast-change', render); render();
  return {panel, places: data.places, show({popup = true} = {}) {
   const bounds = L.latLngBounds([[36.615, 127.322], [36.632, 127.342]]);
   if (fitBounds) fitBounds(bounds); else map.fitBounds(bounds);
   render(); if (popup) venueMarkers.get('osco:venue')?.openPopup();
  }, snapshot: () => ({loaded: !!context, loading, failed, rendered, selected: kinds.filter(([k]) => checkboxes[k].checked).map(([k]) => k)}),
  destroy() {disposed = true; map.off('moveend', render); document.removeEventListener('donghaeng-contrast-change', render); markers.remove(); layers.remove();}};
 }
 root.OscoMap = {create, inScope, places};
})(globalThis);
