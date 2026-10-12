// A static, maximum-height night clock. Geometry is stable for all digits.
function createNightClockScreen(settings) {
  const element = document.createElement('div');
  element.className = 'screen clock-night';
  element.style.cssText = 'background:#000;z-index:900;';
  const canvas = document.createElement('canvas');
  canvas.width = settings.display_width || 1480;
  canvas.height = settings.display_height || 320;
  canvas.style.cssText = 'width:100%;height:100%;object-fit:contain';
  canvas.setAttribute('role', 'img');element.appendChild(canvas);
  const ctx = canvas.getContext('2d');
  const family = "'Segoe UI Light','Helvetica Neue',Arial,sans-serif";
  const colors = {amber:'#ba7a36',red:'#ad4437',white:'#b8aa96'};
  let lastKey = '';
  function draw(currentSettings=settings, now=new Date()) {
    const p = clockDisplayParts(now,currentSettings);
    const key = p.hh+p.mm+p.ampm+currentSettings.night_color;
    if(key===lastKey)return;
    lastKey=key;
    const w=canvas.width,h=canvas.height,padding=h*12/320;
    ctx.font='400 100px '+family;
    const digits=[...'0123456789'].map(d=>ctx.measureText(d));
    const ascent=Math.max(...digits.map(m=>m.actualBoundingBoxAscent));
    const descent=Math.max(...digits.map(m=>m.actualBoundingBoxDescent));
    const digitWidth=Math.max(...digits.map(m=>m.width));
    const colonWidth=ctx.measureText(':').width*.69;
    const size=Math.min((h-padding*2)/(ascent+descent),(w-padding*4)/(digitWidth*4+colonWidth+16))*100;
    const scale=size/100,cell=digitWidth*scale,gap=8*scale,colon=colonWidth*scale;
    const total=cell*4+colon+gap*2,baseline=(h+(ascent-descent)*scale)/2;
    ctx.fillStyle='#000';ctx.fillRect(0,0,w,h);
    ctx.font='400 '+size+'px '+family;ctx.fillStyle=colors[currentSettings.night_color]||colors.amber;ctx.textAlign='center';
    let x=(w-total)/2;
    for(const digit of p.hh){ctx.fillText(digit,x+cell/2,baseline);x+=cell;}
    ctx.save();ctx.globalAlpha=.65;ctx.font='400 '+size*.69+'px '+family;
    const cm=ctx.measureText(':');
    ctx.fillText(':',x+gap+colon/2,(h+cm.actualBoundingBoxAscent-cm.actualBoundingBoxDescent)/2);
    ctx.restore();x+=gap*2+colon;
    for(const digit of p.mm){ctx.fillText(digit,x+cell/2,baseline);x+=cell;}
    // Keep the approved four-digit layout in 12h mode; AM/PM remains accessible.
    canvas.setAttribute('aria-label',`${p.hh}:${p.mm} ${p.ampm}`.trim());
    canvas.dataset.time=p.hh+p.mm;
  }
  return {element,isClock:true,onMount(){draw(settings);},onUnmount(){},onTick(_status,currentSettings,now){draw(currentSettings,now);}};
}
