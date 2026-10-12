const assert = require('node:assert/strict');
const fs = require('node:fs');
const vm = require('node:vm');
const path = require('node:path');
let handler, removed = false, now = 1000;
const messages = [];
const frame = {style:{}, contentWindow:{postMessage:(message, origin)=>messages.push({message,origin})}};
const context = vm.createContext({
  document:{createElement:tag=>tag==='iframe'?frame:{appendChild(){}}},
  location:{origin:'http://pi:8080'}, Date:{now:()=>now},
  window:{addEventListener:(name,fn)=>handler=fn,removeEventListener:(name,fn)=>removed=fn===handler},
});
vm.runInContext(fs.readFileSync(path.join(__dirname,'../frontend/js/screens/journey.js'),'utf8'),context);
const screen = vm.runInContext('createJourneyScreen()',context);
assert.equal(screen.isAvailable(),false);
handler({origin:'http://untrusted',source:frame.contentWindow,data:{type:'camper-journey-state',available:true}});
assert.equal(screen.isAvailable(),false);
handler({origin:'http://pi:8080',source:frame.contentWindow,data:{type:'camper-journey-state',available:true}});
assert.equal(screen.isAvailable(),true);
screen.onMount();screen.onUnmount();
assert.equal(messages[0].message.active,true);assert.equal(messages[1].message.active,false);
assert.equal(messages[0].origin,'http://pi:8080');
now+=21000;assert.equal(screen.isAvailable(),false);
screen.onDispose();assert.equal(removed,true);
assert.equal(frame.src,'/journey?embedded=1');
console.log('Journey module: readiness, origin/source checks, stale data, active-only rendering and cleanup OK');
