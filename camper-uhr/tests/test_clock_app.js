const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const vm = require('node:vm');
class Element {
  constructor(){
    this.children=[];this.style={setProperty(){}};this.dataset={};this.listeners={};
    const classes=new Set();
    this.classList={toggle(name,on){if(on===undefined)on=!classes.has(name);on?classes.add(name):classes.delete(name);},contains:name=>classes.has(name)};
  }
  set innerHTML(_){this.children=[];}
  appendChild(child){this.children.push(child);}
  addEventListener(type,handler){this.listeners[type]=handler;}
  setAttribute(){}
  remove(){}
}
const intervals=[], timers=[];
const body=new Element();
const screen = (id)=>({element:new Element(),isClock:true,themeId:id,ticks:0,unmounts:0,onMount(){},onUnmount(){this.unmounts++;},onTick(){this.ticks++;}});
const context=vm.createContext({console,document:{body,getElementById:()=>new Element(),createElement:()=>new Element()},window:{addEventListener(){},innerWidth:1480,innerHeight:320},setTimeout:(fn,ms)=>{timers.push(ms);return timers.length},clearTimeout(){},setInterval:fn=>intervals.push(fn),createClockScreen:(_s,id)=>screen(id),createPanoramaClockScreen:()=>screen('panorama'),createLedClockScreen:()=>screen('led'),createLinearClockScreen:()=>screen('linear'),createMarbleClockScreen:()=>screen('marble')});
context.createPhotoFrameScreen=()=>screen('photo-frame');
for(const name of ['Trip','Map','Weather','Sun','News','Calendar'])context['create'+name+'Screen']=()=>({element:new Element()});
context.createNightClockScreen=()=>screen('night');
context.createArrivalScreen=()=>screen('arrival');
context.createJourneyScreen=()=>screen('journey');
vm.runInContext(fs.readFileSync(path.join(__dirname,'../frontend/js/app.js'),'utf8'),context);
const app=vm.runInContext('new App()',context);
const ids=['clock_flip','clock_blue','clock_blank','clock_panorama','clock_led','clock_linear','clock_marble'];
const settings={theme:'blue',theme_background_colors:{flip:'#010203',blue:'#040506'},screens:ids.map((id,i)=>({id,stand_enabled:true,drive_enabled:i%2===0,stand_duration_seconds:10+i,drive_duration_seconds:30+i}))};
app.fetchSettings=async()=>settings;
app.startPolling=()=>{};
app.startSettingsSync=()=>{};
app.attachTouch=()=>{};
(async()=>{
  await app.init();
  assert.deepEqual(Array.from(app.screens,s=>s.moduleId),ids);
  assert.equal(app.screens[0].themeId,'flip'); // Independent of old global choice 'blue'.
  assert.equal(body.style.background,'#010203');
  assert.equal(timers.at(-1),10000);
  assert.ok(app.qrTriggerEl.classList.contains('enabled'));
  app.showPhotoQr();assert.equal(app.displaySuspended,'qr');assert.ok(app.qrScreenEl.classList.contains('screen-active'));
  app.qrVisibleUntil=0;app.updateDisplayState();assert.equal(app.displaySuspended,'');
  const first=app.screens[0],beforeGo=first.unmounts;app.goTo(1);assert.equal(first.unmounts,beforeGo+1);assert.equal(timers.at(-1),11000);assert.equal(body.style.background,'#040506');
  app.goTo(4);const active=app.screens[4];const hidden=app.screens[0];const count=hidden.ticks;
  assert.equal(app.status,null);intervals[0]();assert.equal(active.ticks,1);assert.equal(hidden.ticks,count);
  app.mode='drive';app.buildScreens();assert.equal(active.unmounts,1);
  assert.deepEqual(Array.from(app.screens,s=>s.moduleId),['clock_flip','clock_blank','clock_led','clock_marble']);
  app.goTo(2);assert.equal(timers.at(-1),34000);
  const day=app.screens[2],dayTicks=day.ticks;
  app.status={display:{display_on:true,night_clock_active:true,brightness_percent:5}};
  app.updateDisplayState();app.applyBrightness();
  assert.equal(app.displaySuspended,'night');assert.equal(app.dimmerEl.style.opacity,'0.95');
  const rotations=timers.length;app.resetRotation();app.goBy(1);intervals[0]();
  assert.equal(timers.length,rotations);assert.equal(day.ticks,dayTicks);assert.ok(app.nightScreen.ticks>0);
  app.status.display.brightness_control='hardware';app.applyBrightness();assert.equal(app.dimmerEl.style.opacity,'0');
  app.status.display.display_on=false;app.updateDisplayState();assert.equal(app.displaySuspended,'off');
  const nightTicks=app.nightScreen.ticks;intervals[0]();assert.equal(app.nightScreen.ticks,nightTicks);
  app.status.display={display_on:true,night_clock_active:false,brightness_percent:40};
  app.updateDisplayState();app.applyBrightness();assert.equal(app.displaySuspended,'');
  assert.equal(app.currentIndex,2);assert.equal(app.dimmerEl.style.opacity,'0.6');assert.ok(timers.length>rotations);
  app.status.arrival={event_id:'one',expires_at:Date.now()/1000+30,data:{place:'Anfo'}};
  app.updateDisplayState();assert.equal(app.displaySuspended,'arrival');
  const arrivalRotations=timers.length;app.resetRotation();assert.equal(timers.length,arrivalRotations);
  app.status.arrival.expires_at=0;intervals[0]();assert.equal(app.displaySuspended,'');assert.equal(app.currentIndex,2);
  app.status.arrival={event_id:'two',expires_at:Date.now()/1000+30,data:{}};
  app.status.display.night_clock_active=true;app.updateDisplayState();assert.equal(app.displaySuspended,'night');
  app.status.display.night_clock_active=false;app.updateDisplayState();assert.equal(app.displaySuspended,'');
  app.status.arrival={event_id:'three',expires_at:Date.now()/1000+30,data:{}};
  app.updateDisplayState();assert.equal(app.displaySuspended,'arrival');
  app.dismissedArrivalId='three';app.updateDisplayState();assert.equal(app.displaySuspended,'');
  console.log('clock app: seven factories, independent themes/profiles/durations and offline active-only ticking OK');
})().catch(error=>{console.error(error);process.exitCode=1});
