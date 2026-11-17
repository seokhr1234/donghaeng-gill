export function setupApiSettings({bridge, native, onChanged, getStatus = () => bridge.status()}) {
 const doc = document, el = (tag, text) => {const e = doc.createElement(tag); if (text) e.textContent = text; return e;};
 const opener = el('button', 'API 설정'); opener.type = 'button'; opener.className = 'secondary android-key-button';
 opener.style.cssText = 'font-size:11px;padding:6px 9px;min-height:44px;border-radius:12px;margin-left:auto';
 opener.setAttribute('aria-haspopup', 'dialog');
 const dialog = el('dialog'); dialog.id = 'android-api-settings'; dialog.setAttribute('aria-labelledby', 'android-api-title');
 const head = el('div'); head.className = 'dialog-head';
 const title = el('h2', 'API 설정'); title.id = 'android-api-title';
 const close = el('button', '×'); close.type = 'button'; close.setAttribute('aria-label', 'API 설정 닫기'); close.onclick = () => dialog.close();
 head.append(title, close); dialog.append(head);
 const trafficTitle = el('h3', '대중교통 · ODsay'), traffic = el('p'); traffic.role = 'status'; traffic.id = 'android-traffic-key-state';
 const aiTitle = el('h3', 'AI · Gemini'), ai = el('p'); ai.role = 'status'; ai.id = 'android-gemini-key-state';
 const message = el('p'); message.role = 'status'; message.id = 'android-key-message';
 const buttons = [];
 function button(text, method) {
  const b = el('button', text); b.type = 'button'; b.className = 'secondary';
  b.style.cssText = 'display:block;width:100%;margin:8px 0;min-height:44px'; buttons.push(b);
  b.onclick = async () => {
   buttons.forEach(x => x.disabled = true); message.textContent = '';
   try {
    const result = await bridge[method]();
    if (result?.changed) {onChanged?.(result); message.textContent = '설정을 반영했습니다. 실제 연결은 길 찾기에서 확인해 주세요.';}
    await refresh();
   } catch {message.textContent = '설정을 완료하지 못했어요. 키 입력 형식과 기기 상태를 확인해 주세요.';}
   finally {buttons.forEach(x => x.disabled = false);}
  };
  return b;
 }
 const restore = button('대중교통 내장 키 복원', 'resetKey');
 dialog.append(trafficTitle, traffic, el('p', '키 입력창은 보안을 위해 비워 둡니다. 적용됨으로 표시되면 다시 입력할 필요가 없어요.'),
  button('대중교통 키 입력·변경', 'configureKey'), restore, aiTitle, ai,
  button('Gemini API 키 입력·변경', 'configureGemini'), button('Gemini 기기 키 삭제 · 서버 사용', 'clearGemini'),
  el('p', '입력한 Gemini 키는 이 기기의 네이티브 설정에 저장합니다. 개인 키를 사용하면 상태 문장과 익명 경로 요약을 Google에 직접 보냅니다. 좌표·목적지 이름·지도 도형은 자동 전송하지 않아요.'),
  el('p', '개인 Gemini 키가 없으면 기존 Vercel 서버 설정을 사용합니다. 입력된 키 값은 화면이나 웹 저장소에 표시하지 않습니다.'), message);
 const issue = el('a', 'Google AI Studio에서 Gemini 키 발급'); issue.href = 'https://aistudio.google.com/apikey'; issue.target = '_blank'; issue.rel = 'noopener noreferrer'; dialog.append(issue);
 async function refresh() {
  const s = await getStatus();
  traffic.textContent = s.keySource === 'bundled' ? 'APK 내장 키 적용 중 · 새 입력 불필요' :
   s.keySource === 'device' ? '기기에 입력한 키 적용 중' : s.configured ? '교통 키 적용 중' : s.bundledKeyAvailable ? '교통 키 미설정 · 새 키를 입력하거나 내장 키를 복원해 주세요.' : '공개 배포판은 교통 키 미내장 · 아래에서 본인의 ODsay Android 키를 입력해 주세요.';
  restore.hidden = !s.bundledKeyAvailable;
  if (s.geminiConfigured) ai.textContent = '기기에 입력한 Gemini 키 적용 중 · 실제 연결은 요청 시 확인';
  else {
   ai.textContent = '개인 Gemini 키 없음 · 서버 설정 확인 중…';
   try {
    const r = await native('backend', {path: '/api/status', method: 'GET', body: ''});
    const server = JSON.parse(r.body);
    ai.textContent = r.status !== 200 ? '개인 키 없음 · 서버 상태 미확인' : server.configured ? '개인 키 없음 · 서버 Gemini 설정 있음' : '개인 키 없음 · 서버 Gemini 미설정';
   } catch {ai.textContent = '개인 키 없음 · 서버 상태 미확인. 아래에서 개인 키를 입력할 수 있어요.';}
  }
 }
 opener.onclick = () => {message.textContent = ''; dialog.showModal(); refresh().catch(() => {message.textContent = '기기 설정을 읽지 못했어요. 앱을 다시 열어 주세요.';});};
 dialog.addEventListener('close', () => opener.focus());
 doc.querySelector('.header')?.append(opener); doc.body.append(dialog);
 return {refresh, dialog};
}
