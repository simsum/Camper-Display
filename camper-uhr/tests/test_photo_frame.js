const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const vm = require('node:vm');

class Node {
  constructor(){this.style={};this.dataset={};this.textContent='';this.attributes={};}
  setAttribute(key,value){this.attributes[key]=value;}
  removeAttribute(key){delete this.attributes[key];}
}
const tiles = Array.from({length:5},()=>{
  const tile=new Node(),background=new Node(),image=new Node(),meta=new Node(),date=new Node(),place=new Node();
  tile.querySelector=selector=>({'.photo-frame-background':background,'.photo-frame-image':image,'.photo-frame-meta':meta,'.photo-frame-meta span':date,'.photo-frame-meta strong':place}[selector]);
  return {tile,background,image,meta,date,place};
});
const grid=new Node(),pageBackground=new Node(),root=new Node();
root.querySelector=selector=>({'.photo-frame-grid':grid,'.photo-frame-page-background':pageBackground}[selector]);
root.querySelectorAll=selector=>selector==='.photo-frame-tile'?tiles.map(item=>item.tile):[];
const context = vm.createContext({
  console, Date, module:{exports:{}}, globalThis:{fetch:null},
  document:{createElement:()=>root},
});
vm.runInContext(fs.readFileSync(path.join(__dirname,'../frontend/js/screens/photo-frame.js'),'utf8'),context);
const {adaptivePhotoPages,createPhotoFrameScreen,photoAspect,photoFormat}=context.module.exports;
const photos = [
  {id:'wide',url:'/wide.jpg',aspect_ratio:2.75,taken_at:1789725600,place:'Bamberg · Deutschland'},
  {id:'landscape-a',url:'/landscape-a.jpg',aspect_ratio:1.78,place:'Bozen · Italien'},
  {id:'landscape-b',url:'/landscape-b.jpg',aspect_ratio:1.5},
  {id:'portrait-a',url:'/portrait-a.jpg',aspect_ratio:.75,place:'Garda · Italien'},
  {id:'portrait-b',url:'/portrait-b.jpg',aspect_ratio:.67},
  {id:'square',url:'/square.jpg',aspect_ratio:1},
  {id:'portrait-c',url:'/portrait-c.jpg',aspect_ratio:.8},
  {id:'portrait-d',url:'/portrait-d.jpg',aspect_ratio:.67},
  {id:'landscape-c',url:'/landscape-c.jpg',aspect_ratio:1.33},
];
assert.equal(photoAspect({width:1200,height:800}),1.5);
assert.equal(photoAspect({aspect_ratio:.2}),.42);
assert.equal(photoFormat({aspect_ratio:2.1}),'panorama');
assert.equal(photoFormat({aspect_ratio:1.5}),'landscape');
assert.equal(photoFormat({aspect_ratio:1}),'square');
assert.equal(photoFormat({aspect_ratio:.75}),'portrait');
const pages=adaptivePhotoPages(photos);
assert.ok(pages.length>=2);
assert.deepEqual(Array.from(pages.flat(),photo=>photo.id).sort(),photos.map(photo=>photo.id).sort());
assert.ok(pages.every(batch=>batch.length>=1&&batch.length<=5));
assert.ok(pages.some(batch=>batch.length!==3),'adaptive layout must not remain fixed at three');
assert.ok(pages.every(batch=>batch.every(photo=>photoFormat(photo)===photoFormat(batch[0]))));
assert.ok(pages.filter(batch=>photoFormat(batch[0])==='panorama').every(batch=>batch.length===1));
assert.ok(pages.filter(batch=>photoFormat(batch[0])==='landscape').every(batch=>batch.length<=3));
assert.ok(pages.filter(batch=>photoFormat(batch[0])==='square').every(batch=>batch.length<=4));
assert.ok(pages.filter(batch=>photoFormat(batch[0])==='portrait').every(batch=>batch.length<=5));
const piMix = [
  {id:'panorama',aspect_ratio:2.4},
  ...Array.from({length:17},(_,index)=>({id:`landscape-${index}`,aspect_ratio:index%2?1.33:1.78})),
  ...Array.from({length:24},(_,index)=>({id:`portrait-${index}`,aspect_ratio:index%2?.67:.75})),
];
const piPages=adaptivePhotoPages(piMix);
assert.ok(piPages.filter(batch=>photoFormat(batch[0])==='landscape').every(batch=>batch.length>=2&&batch.length<=3));
assert.ok(piPages.filter(batch=>photoFormat(batch[0])==='portrait').every(batch=>batch.length>=2&&batch.length<=5));

const screen = createPhotoFrameScreen({initialPhotos:photos,fetcher:null});
assert.equal(screen.isAvailable(),true);
const firstPage=pages[0];
assert.deepEqual(tiles.slice(0,firstPage.length).map(item=>item.image.src),Array.from(firstPage,photo=>photo.url));
assert.equal(tiles[firstPage.length]?.tile.style.display,'none');
assert.equal(tiles[0].place.textContent,'Bamberg · Deutschland');
assert.match(tiles[0].date.textContent,/\d{2}\.\d{2}\.\d{4}/);
assert.match(grid.style.gridTemplateColumns,/px/);
assert.match(pageBackground.style.backgroundImage,/wide\.jpg/);

screen.nextPage();
const secondPage=pages[1];
assert.deepEqual(tiles.slice(0,secondPage.length).map(item=>item.image.src),Array.from(secondPage,photo=>photo.url));
screen.onDispose();
const empty = createPhotoFrameScreen({initialPhotos:[],fetcher:null});
assert.equal(empty.isAvailable(),false);
console.log(`photo frame: adaptive ${pages.map(batch=>batch.length).join('+')} layout, metadata, navigation and cleanup OK`);
