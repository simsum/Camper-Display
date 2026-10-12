const assert = require('node:assert/strict');
const {extractPhotoMetadata,parseExifDate,parseJpegExif}=require('../frontend/js/photo-metadata.js');

function exifFixture(){
  const buffer=new ArrayBuffer(260),view=new DataView(buffer),bytes=new Uint8Array(buffer),tiff=12;
  view.setUint16(0,0xffd8);view.setUint16(2,0xffe1);view.setUint16(4,256);
  bytes.set(Buffer.from('Exif\0\0','binary'),6);
  view.setUint16(tiff,0x4949);view.setUint16(tiff+2,42,true);view.setUint32(tiff+4,8,true);
  const u16=(p,v)=>view.setUint16(tiff+p,v,true),u32=(p,v)=>view.setUint32(tiff+p,v,true);
  u16(8,2);
  u16(10,0x8769);u16(12,4);u32(14,1);u32(18,38);
  u16(22,0x8825);u16(24,4);u32(26,1);u32(30,80);
  u16(38,1);u16(40,0x9003);u16(42,2);u32(44,20);u32(48,140);
  bytes.set(Buffer.from('2024:05:06 14:23:10\0','binary'),tiff+140);
  u16(80,4);
  u16(82,1);u16(84,2);u32(86,2);bytes[tiff+90]='N'.charCodeAt(0);
  u16(94,2);u16(96,5);u32(98,3);u32(102,160);
  u16(106,3);u16(108,2);u32(110,2);bytes[tiff+114]='E'.charCodeAt(0);
  u16(118,4);u16(120,5);u32(122,3);u32(126,184);
  [[49,1],[53,1],[24,1],[10,1],[53,1],[24,1]].forEach(([n,d],index)=>{u32(160+index*8,n);u32(164+index*8,d);});
  return buffer;
}

assert.equal(parseExifDate('2024:05:06 14:23:10'),new Date(2024,4,6,14,23,10).getTime()/1000);
const metadata=parseJpegExif(exifFixture());
assert.equal(metadata.takenAt,new Date(2024,4,6,14,23,10).getTime()/1000);
assert.ok(Math.abs(metadata.latitude-49.89)<1e-6);
assert.ok(Math.abs(metadata.longitude-10.89)<1e-6);
(async()=>{
  const fallback=await extractPhotoMetadata({type:'image/png',lastModified:1700000000000});
  assert.equal(fallback.takenAt,1700000000);
  console.log('photo metadata: EXIF date/GPS parsing and file-date fallback OK');
})().catch(error=>{console.error(error);process.exitCode=1});
