(function (root) {
 'use strict';
 const asset = 'bundled-luna-demo-slopes';
 const minZoom = 17;
 const colors = ['#237570', '#a26b15', '#a0344e'];
 const point = value => Array.isArray(value) && value.length === 2 && value.every(Number.isFinite);
 const grade = number => number.toFixed(1).replace(/\.0$/, '');

 function description(segment) {
  if (segment.kind === 'bridge_assumption') return '육교 쪽이 주변 길보다 완만하다는 시연 가정이에요. 실제 경사와 엘리베이터 운행은 미확인이에요.';
  if (!segment.grade) return '경사율 미확인';
  const [low, high] = segment.grade;
  const value = grade(low) === grade(high) ? grade(high) : grade(low) + '–' + grade(high);
  return (segment.kind === 'registered' ? '등록 경사 ' : '참고 경사 추정 ') + value + '%';
 }

 function create(map, panel) {
  const L = root.L;
  const label = document.createElement('label');
  label.className = 'map-slope-toggle';
  const enabled = document.createElement('input');
  enabled.type = 'checkbox'; enabled.id = 'slope-luna-demo'; enabled.checked = true;
  label.append(enabled, document.createTextNode('루나밸리 서쪽·남쪽 경사'));
  const focus = document.createElement('button');
  focus.type = 'button'; focus.className = 'secondary'; focus.textContent = '루나밸리 주변 보기';
  const legend = document.createElement('p');
  legend.className = 'map-slope-note';
  legend.textContent = '시연용 · 청록 5% 미만, 황토 5% 이상 10% 미만, 자주 10% 이상. 짧은 점선은 경사 미확인, 긴 점선은 육교예요.';
  const status = document.createElement('p');
  status.className = 'map-slope-status'; status.role = 'status';
  panel.append(label, focus, legend, status);
  const pane = map.createPane('luna-demo-slopes');
  pane.style.zIndex = '392';
  const renderer = L.canvas({pane: 'luna-demo-slopes'});
  const layer = L.featureGroup();
  let data, pending, failed = false, destroyed = false;

  async function load() {
   if (data || pending || destroyed) return pending;
   const original = document.getElementById(asset).cloneNode(true);
   failed = false;
   pending = (async () => {
    try {
     const parsed = JSON.parse(await root.DONGHAENG_LOAD_DATA(asset));
     if (parsed.schema !== 'donghaeng-luna-demo-slopes-v1' || parsed.display_only !== true ||
         parsed.routing_eligible !== false || parsed.field_verified !== false ||
         !point(parsed.focus) || !Array.isArray(parsed.segments) || !parsed.segments.length) throw Error('경사 자료 형식 오류');
     if (destroyed) return;
     for (const segment of parsed.segments) {
      const [a, b] = segment.coordinates;
      const bridge = segment.kind === 'bridge_assumption';
      const high = segment.grade?.[1];
      const color = bridge ? '#63458b' : high == null ? '#646f75' : colors[high >= 10 ? 2 : high >= 5 ? 1 : 0];
      const line = L.polyline([a, b], {pane: 'luna-demo-slopes', renderer, color, weight: bridge ? 6 : 4,
       dashArray: bridge ? '10 5' : high == null ? '3 6' : null, contrastRole: bridge ? 'alternative' : high == null ? 'unverified' : 'context'});
      const popup = document.createElement('div');
      const name = document.createElement('strong');
      name.textContent = segment.name || '보행로';
      const value = document.createElement('p');
      value.textContent = description(segment);
      popup.append(name, value);
      line.bindPopup(popup).addTo(layer);
     }
     data = parsed;
    } catch {
     layer.clearLayers();
     document.getElementById(asset)?.replaceWith(original);
     failed = true;
    } finally {
     pending = null;
     render();
    }
   })();
   return pending;
  }

  function render() {
   if (destroyed) return;
   const zoomed = map.getZoom() >= minZoom;
   if (enabled.checked && zoomed && !data && !pending && !failed) void load();
   const visible = enabled.checked && zoomed && data && map.getBounds().pad(.1).intersects(layer.getBounds());
   if (visible && !map.hasLayer(layer)) layer.addTo(map);
   if (!visible) layer.remove();
   status.textContent = enabled.checked && failed ? '루나밸리 경사를 읽지 못했어요. 주변 보기로 다시 시도해 주세요.' :
    visible ? '선을 누르면 해당 구간을 확인할 수 있어요.' : '';
   status.hidden = !status.textContent;
  }

  focus.onclick = async () => {
   enabled.checked = true;
   await load();
   if (data && !destroyed) map.setView(data.focus, 18, {animate: false});
   render();
  };
  enabled.onchange = () => { if (enabled.checked) failed = false; render(); };
  map.on('moveend', render);
  render();
  return () => {
   destroyed = true;
   map.off('moveend', render);
   layer.remove();
   if (map.hasLayer(renderer)) renderer.remove();
  };
 }

 root.LunaDemoSlopes = {create};
})(globalThis);
