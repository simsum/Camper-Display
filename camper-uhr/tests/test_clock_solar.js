const assert=require('node:assert/strict'),fs=require('node:fs'),vm=require('node:vm'),path=require('node:path');
const ctx=vm.createContext({Date,String,Number,Math});
vm.runInContext(fs.readFileSync(path.join(__dirname,'../frontend/js/screens/clock-designs.js'),'utf8'),ctx);
const now=new Date(2026,8,11,12,0,0);
function status(rise='06:44',set='19:41',day='2026-09-11') { return {server_time_iso:now.toISOString(),weather:{available:true,sunrise:day+'T'+rise,sunset:day+'T'+set}}; }
const solar=ctx.clockSolarBand(status(),now);
assert.equal(solar.available,true);assert.equal(solar.sunrise,404);assert.equal(solar.sunset,1181);
assert.equal(solar.period,'Tag');assert.equal(solar.times,'↑ 06:44 · ↓ 19:41');
assert.ok(solar.background.includes('#ba786c 28.0556%'));
assert.ok(solar.background.includes('#bc736b 82.0139%'));
assert.notEqual(ctx.clockSolarBand(status('08:10','16:20'),now).background,solar.background);
for(const [h,m,expected] of [[6,43,'Nacht'],[6,44,'Tag'],[19,40,'Tag'],[19,41,'Nacht']]) {
  const date=new Date(2026,8,11,h,m);const value=status();value.server_time_iso=date.toISOString();
  assert.equal(ctx.clockSolarBand(value,date).period,expected);
}
for(const value of [null,{weather:{available:false}},status('06:44','19:41','2026-09-10'),status('broken'),status('20:00','06:00'),status('12:00','12:00')]) {
  assert.equal(ctx.clockSolarBand(value,now).available,false);
}
const stale=status();stale.server_time_iso=new Date(now.getTime()-7200001).toISOString();assert.equal(ctx.clockSolarBand(stale,now).available,false);
const offset=status();offset.weather.sunrise=new Date(2026,8,11,7,15).toISOString();offset.weather.sunset=new Date(2026,8,11,18,30).toISOString();
assert.equal(ctx.clockSolarBand(offset,now).sunrise,435);
const nearEdges=ctx.clockSolarBand(status('00:10','23:50'),now);
const stops=Array.from(nearEdges.background.matchAll(/ (\d+\.\d+)%/g),m=>Number(m[1]));
assert.ok(stops.every((v,i)=>v>=0&&v<=100&&(!i||v>=stops[i-1])));
console.log('panorama solar: real time anchors, seasonal changes, day/night, stale/missing data, offsets and edge gradients OK');
