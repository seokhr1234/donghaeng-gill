import assert from 'node:assert/strict';
import {createRequire} from 'node:module';
import {createApp} from '../server.mjs';

const {chromium} = createRequire(import.meta.url)('playwright');
const server = createApp();
await new Promise(resolve => server.listen(0, '127.0.0.1', resolve));
const url = 'http://127.0.0.1:' + server.address().port;
let browser;
try {
 browser = await chromium.launch({executablePath:process.env.CHROME_PATH || '/usr/bin/chromium', args:['--no-sandbox']});
 for (const [width,height] of [[320,568],[393,852],[667,375],[844,390]]) {
  const context = await browser.newContext({viewport:{width,height}, isMobile:true, hasTouch:true, reducedMotion:'reduce'});
  await context.route('https://**',route=>route.abort());
  const page = await context.newPage(), errors = [];
  page.on('pageerror',error=>errors.push(error.message));
  const ready = async () => {
   await page.goto(url);
   await page.waitForFunction(()=>!document.querySelector('#find-route').disabled);
  };
  await ready();
  assert(await page.evaluate(()=>isMobileUI()));
  assert(await page.evaluate(()=>document.documentElement.scrollWidth===innerWidth));
  assert.equal(await page.locator('#mobile-api-settings').isVisible(),false);

  for (const night of [false,true]) {
   await page.evaluate(high=>HighContrast.set(high),night);
   await page.locator('#osco-open').tap();
   await page.getByRole('tab',{name:'오스코',exact:true}).tap();
   await page.getByRole('button',{name:'행사장·공식 안내'}).tap();
   const popup=page.locator('#mobile-place-detail');
   await popup.waitFor({state:'visible'});
   assert.equal(await page.locator('.map-layers-control').evaluate(el=>el.open),false);
   await popup.getByRole('button',{name:'출발지로 선택'}).tap();
   assert(await page.evaluate(()=>OscoMap.inScope(origin)));
  }
  await ready();
  await page.getByRole('button',{name:'제보',exact:true}).tap();
  await page.locator('#report-dialog .close').tap();
  assert.equal(await page.evaluate(()=>tripQuestions.snapshot().index),0);
  assert(await page.locator('.question-card').isVisible());
  await page.getByRole('button',{name:'저장',exact:true}).tap();
  await page.locator('#saved-list').getByRole('button',{name:'길 찾기',exact:true}).tap();

  const field=page.locator('#origin-query');
  await field.fill('서울');
  // Samsung WebView resizes its layout viewport, as well as its visual viewport.
  const keyboardHeight=Math.max(260,height-230);
  await page.setViewportSize({width,height:keyboardHeight});
  await page.waitForFunction(()=>document.body.classList.contains('keyboard-open'));
  assert.equal(await page.locator('.mobile-tabs').isVisible(),false);
  const visible=await page.evaluate(()=>{
   const field=document.querySelector('#origin-query').getBoundingClientRect();
   const body=document.querySelector('.question-body').getBoundingClientRect();
   const action=document.querySelector('.question-controls .primary').getBoundingClientRect();
   return field.top>=body.top-1 && field.bottom<=body.bottom+1 && action.bottom<=visualViewport.height;
  });
  assert(visible,`Editor and next button must fit above the keyboard at ${width}x${height}`);
  await page.setViewportSize({width,height});
  await field.blur();
  await page.waitForFunction(()=>!document.body.classList.contains('keyboard-open'));
  assert.equal(await field.inputValue(),'서울');

  await page.evaluate(()=>{
   tripQuestions.close();
   setOrigin([37.5665,126.978],'검사 출발');
   setDestination({name:'검사 도착',ll:[37.573,126.98]},{pan:false});
   setCondition('계단을 피해서 걷고 싶어요.');
  });
  await page.locator('#find-route').tap();
  await page.waitForFunction(()=>!!cityRoute&&document.body.dataset.mobileMode==='results');
  const framed = () => page.evaluate(()=>{
   const rect=map.getContainer().getBoundingClientRect(), sheet=document.querySelector('.sidebar').getBoundingClientRect();
   return cityRoute.coordinates.every(ll=>{
    const point=map.latLngToContainerPoint(ll);
    return point.x>=0 && point.x<=rect.width && point.y>=0 && point.y+rect.top<sheet.top;
   });
  });
  assert(await framed(),`Walking route is obscured at ${width}x${height}`);
  await page.setViewportSize({width:width<700?844:393,height:width<700?390:852});
  await page.waitForTimeout(300);
  assert(await framed(),'Route points must remain above the results sheet after rotation');
  assert.deepEqual(errors,[]);
  console.log(`${width}x${height}: menu, map popups in both themes, keyboard, saved routes, walking and rotation OK`);
  await context.close();
 }
} finally {
 await browser?.close();
 server.closeAllConnections();
 await new Promise(resolve=>server.close(resolve));
}
