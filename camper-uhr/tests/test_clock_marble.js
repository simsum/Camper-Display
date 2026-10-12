const assert=require('node:assert/strict'),fs=require('node:fs'),vm=require('node:vm'),path=require('node:path');
let now=0,reduced=false,nextId=0;const frames=new Map();
const drawing=new Proxy({createLinearGradient:()=>({addColorStop(){}}),createRadialGradient:()=>({addColorStop(){}})},{get:(o,k)=>o[k]||(()=>{}),set:(o,k,v)=>(o[k]=v,true)});
class Element{
  constructor(){this.style={};this.dataset={};this.children=[];this.isConnected=true;this.active=true;this.classList={contains:()=>this.active};}
  appendChild(el){this.children.push(el);}setAttribute(){}getContext(){return drawing;}
}
const document={visibilityState:'visible',createElement:()=>new Element()};
const context=vm.createContext({Date,Math,document,performance:{now:()=>now},matchMedia:()=>({matches:reduced}),requestAnimationFrame:fn=>{frames.set(++nextId,fn);return nextId},cancelAnimationFrame:id=>frames.delete(id)});
for(const name of ['clock-designs','clock-marble'])vm.runInContext(fs.readFileSync(path.join(__dirname,`../frontend/js/screens/${name}.js`),'utf8'),context);
for(let h=0;h<24;h++)for(let m=0;m<60;m++){
  const key=String(h).padStart(2,'0')+String(m).padStart(2,'0'),points=context.marbleClockTargets(key);
  assert.equal(points.length,112);assert.equal(new Set(points.map(p=>`${p.x},${p.y}`)).size,112);
  assert.ok(points.every(p=>p.x>0&&p.x<1480&&p.y>0&&p.y<320));
}
const settings={time_format_24h:true},screen=context.createMarbleClockScreen(settings),canvas=screen.element.children[0];
const update=(h,m,s)=>screen.onTick(null,settings,new Date(2026,8,11,h,m,s));
const frame=t=>{now=t;const callbacks=[...frames.values()];frames.clear();callbacks.forEach(fn=>fn(t));};
update(21,34,58);const idle=canvas.dataset.drawCount;
update(21,34,59);update(21,34,59);assert.equal(canvas.dataset.drawCount,idle);assert.equal(frames.size,0);
update(21,35,0);assert.equal(canvas.dataset.animating,'true');assert.equal(frames.size,1);
update(21,35,0);assert.equal(frames.size,1);frame(100);assert.ok(Number(canvas.dataset.drawCount)>Number(idle));
for(let t=110;t<=5100;t+=10)frame(t);
assert.equal(canvas.dataset.animating,'false');assert.equal(frames.size,0);assert.equal(canvas.dataset.time,'2135');
assert.ok(Number(canvas.dataset.drawCount)-Number(idle)<=123,'Frame cap exceeded');
update(21,35,59);update(21,36,0);screen.onUnmount();const stopped=canvas.dataset.drawCount;frame(5300);
assert.equal(frames.size,0);assert.equal(canvas.dataset.drawCount,stopped);
update(21,36,59);update(21,37,0);document.visibilityState='hidden';frame(5400);assert.equal(frames.size,0);
document.visibilityState='visible';update(21,37,1);assert.equal(canvas.dataset.animating,'false');assert.equal(canvas.dataset.time,'2137');
screen.element.active=false;const hidden=canvas.dataset.drawCount;update(21,38,0);assert.equal(canvas.dataset.drawCount,hidden);
screen.element.active=true;update(21,38,0);assert.equal(canvas.dataset.time,'2138');assert.equal(frames.size,0);
reduced=true;update(21,38,59);update(21,39,0);assert.equal(frames.size,0);
settings.time_format_24h=false;update(21,39,0);assert.equal(canvas.dataset.time,'0939');assert.equal(frames.size,0);
console.log('marble: 1440 layouts, idle zero redraw, bounded animation, final time, duplicate ticks, unmount/visibility/reduced motion and format change OK');
