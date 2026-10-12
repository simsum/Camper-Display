const assert = require('node:assert/strict');
const fs = require('node:fs');
const vm = require('node:vm');
const path = require('node:path');
const context = vm.createContext({Date, String, Array, Number});
const clockSource = fs.readFileSync(path.join(__dirname, '../frontend/js/screens/clock-designs.js'), 'utf8');
vm.runInContext(clockSource, context);
assert.doesNotMatch(clockSource, /data-clock="month"/);
const clockCss = fs.readFileSync(path.join(__dirname, '../frontend/css/clock-designs.css'), 'utf8');
assert.doesNotMatch(clockCss, /\.clock-led::before/);
assert.doesNotMatch(clockCss, /\.clock-led\s*\{[^}]*box-shadow/);
const layoutSource = fs.readFileSync(path.join(__dirname, '../frontend/css/layout.css'), 'utf8');
const appSource = fs.readFileSync(path.join(__dirname, '../frontend/js/app.js'), 'utf8');
const indexSource = fs.readFileSync(path.join(__dirname, '../frontend/index.html'), 'utf8');
assert.doesNotMatch(layoutSource, /\.dots?\b/);
assert.doesNotMatch(appSource, /dotsEl|className\s*=\s*["']dot["']/);
assert.doesNotMatch(indexSource, /id=["']dots["']/);
for (const hour of [0, 1, 11, 12, 13, 23]) {
  const now = new Date(2026, 8, 11, hour, 59, 58);
  const a = context.clockDisplayParts(now, {time_format_24h:true});
  assert.equal(a.hh, String(hour).padStart(2,'0'));
  assert.equal(a.ampm, '');
  const b = context.clockDisplayParts(now, {time_format_24h:false});
  assert.equal(b.hour, hour % 12 || 12);
  assert.equal(b.ampm, hour < 12 ? 'AM' : 'PM');
  assert.equal(a.progress, b.progress);
  assert.equal(b.ss,'58');
}
const before = context.clockDisplayParts(new Date(2026,11,31,23,59,59));
const after = context.clockDisplayParts(new Date(2027,0,1,0,0,0));
assert.notEqual(before.dateKey,after.dateKey);
assert.equal(after.progress,0);
assert.ok(before.progress<1 && before.progress>.9999);
assert.deepEqual(Array.from(context.clockRulerValues(0,24)),[20,21,22,23,0,1,2,3,4]);
assert.deepEqual(Array.from(context.clockRulerValues(12,12,1)),[8,9,10,11,12,1,2,3,4]);
assert.deepEqual(Array.from(context.clockRulerValues(0,60)),[56,57,58,59,0,1,2,3,4]);
assert.equal(vm.runInContext('CLOCK_LED_GLYPHS.every(g => g.length === 35 && /^[01]+$/.test(g))',context),true);
console.log('clock designs: 12/24h, day/year rollover, ruler wrap and LED glyphs OK');
assert.deepEqual(Array.from(context.clockRulerValues(0,60,0,5)),[55,56,57,58,59,0,1,2,3,4,5]);
for(const [previous,next,modulus] of [[59,0,60],[23,0,24],[12,1,12],[11,12,12],[28,29,60]]) {
  assert.equal(context.clockRulerShouldSlide(previous,next,modulus,1000),true);
}
for(const [previous,next,elapsed] of [[null,1,1000],[1,1,1000],[1,3,1000],[1,0,1000],[1,2,60000],[1,2,-1000],[1,2,0]]) {
  assert.equal(context.clockRulerShouldSlide(previous,next,60,elapsed),false);
}
console.log('linear animation: forward wraps, spare cells and jump suppression OK');
for(const [before,after,expected] of [[59000,60000,true],[3599000,3600000,true],[86399000,86400000,true],[null,60000,false],[60000,60000,false],[60000,61000,false],[1000,60000,false],[61000,60000,false]]) {
  assert.equal(context.clockLedShouldRefresh(before,after),expected);
}
console.log('LED refresh: minute/hour/day boundary, duplicate ticks, jumps and seconds-only updates OK');
for(let target=0;target<10;target++)for(let seed=1;seed<=10;seed++){
  let state=seed;const random=()=>((state=(state*1664525+1013904223)>>>0)/4294967296);
  const frames=context.clockLedRefreshFrames(String(target),random);
  assert.equal(frames[0].at,0);
  assert.equal(frames.at(-1).value,String(target));
  assert.ok(frames.at(-1).at>=1200&&frames.at(-1).at<1650);
  frames.forEach((frame,i)=>{assert.match(frame.value,/^[0-9]$/);if(i)assert.ok(frame.at>frames[i-1].at)});
}
console.log('LED shuffle: 100 seeded sequences, bounded duration, valid random digits, correct final targets OK');
