// Kugelbahn: fixed paths, 112 cached sprites, at most 24 rendered frames/s.
// No physics engine, network calls or recurring animation in the resting state.
function marbleClockLayout(digits) {
  const points=[],chambers=[326,538,826,1038];
  [...digits].forEach((digit,index)=>{
    [...CLOCK_LED_GLYPHS[Number(digit)]].forEach((bit,i)=>{
      if(bit==='1')points.push({x:chambers[index]+44+(i%5)*22,y:69+Math.floor(i/5)*22,r:8.4});
    });
  });
  let spare=0;
  while(points.length<112){points.push({x:83+(spare%10)*13,y:196-Math.floor(spare/10)*13,r:5.6});spare++;}
  return points;
}
function marbleClockTargets(digits) {
  const points=marbleClockLayout(digits);
  return points.map((_,index)=>points[(index*37+19)%112]);
}
function createMarbleClockScreen(settings) {
  const element=document.createElement('div');element.className='screen clock-marble';
  element.style.background='#07121a';
  const canvas=document.createElement('canvas');canvas.width=1480;canvas.height=320;
  canvas.style.cssText='width:100%;height:100%;object-fit:contain';
  canvas.setAttribute('role','img');element.appendChild(canvas);
  let ctx=canvas.getContext('2d'),background=null,sprite=null;
  const chambers=[326,538,826,1038],pixelScale=1;
  const clamp=x=>Math.max(0,Math.min(1,x)),mix=(a,b,t)=>a+(b-a)*t,smooth=t=>t*t*(3-2*t);
  let from=[],to=[],lastKey=null,lastNow=null,lastFormat=null,frameId=null,started=0,lastFrame=-Infinity,ampm='';
  function makeSprite(){
    sprite=document.createElement('canvas');sprite.width=sprite.height=48;
    const c=sprite.getContext('2d'),g=c.createRadialGradient(19,17,1,24,25,18);
    ['#fff7d6','#eaca7b','#b78935','#493415'].forEach((color,i)=>g.addColorStop(i/3,color));
    c.fillStyle=g;c.beginPath();c.arc(24,24,17,0,Math.PI*2);c.fill();
    c.fillStyle='#ffffffb0';c.beginPath();c.ellipse(19,18,4,2.5,-.6,0,Math.PI*2);c.fill();
  }
    function rounded(x,y,w,h,r,fill,stroke){ctx.beginPath();ctx.roundRect(x,y,w,h,r);if(fill){ctx.fillStyle=fill;ctx.fill()}if(stroke){ctx.strokeStyle=stroke;ctx.lineWidth=1.5;ctx.stroke()}}
    function line(points,color,width){ctx.beginPath();points.forEach(([x,y],i)=>i?ctx.lineTo(x,y):ctx.moveTo(x,y));ctx.strokeStyle=color;ctx.lineWidth=width;ctx.lineJoin='round';ctx.lineCap='round';ctx.stroke()}
    function label(text,x,y,size,color,align='left'){ctx.font=`400 ${Math.max(size,22)}px 'Segoe UI',Arial,sans-serif`;ctx.fillStyle=color;ctx.textAlign=align;ctx.fillText(text,x,y)}
    function ball(point){const size=point.r*2.8;ctx.drawImage(sprite,point.x-size/2,point.y-size/2,size,size)}
    function position(index,t){
      const a=from[index],b=to[index],delay=(index%17)/17*.14,p=clamp((t-delay)/(1-delay));
      const lane=(index%3-1)*4,railY=274+lane;
      if(p<.23){const q=p/.23;return {x:a.x+Math.sin(index*2)*8*q,y:mix(a.y,railY,q*q),r:a.r}}
      const dropX=a.x+Math.sin(index*2)*8;
      if(p<.56){const q=(p-.23)/.33;return {x:mix(dropX,1390+lane,q),y:railY-Math.abs(Math.sin(q*Math.PI*5))*5*(1-q),r:a.r}}
      if(p<.72){const q=(p-.56)/.16;return {x:1390+lane,y:mix(railY,29+lane,smooth(q)),r:mix(a.r,b.r,q)}}
      if(p<.89){const q=(p-.72)/.17;return {x:mix(1390+lane,b.x,smooth(q)),y:29+lane,r:b.r}}
      const q=(p-.89)/.11;return {x:b.x,y:mix(29+lane,b.y,smooth(q)),r:b.r};
    }
    function drawScene(){
      ctx.setTransform(pixelScale,0,0,pixelScale,0,0);
      const bg=ctx.createLinearGradient(0,0,1480,320);bg.addColorStop(0,'#08151e');bg.addColorStop(.5,'#152833');bg.addColorStop(1,'#07121a');ctx.fillStyle=bg;ctx.fillRect(0,0,1480,320);
      const wash=ctx.createRadialGradient(760,180,20,760,180,780);wash.addColorStop(0,'#719ca315');wash.addColorStop(1,'#719ca300');ctx.fillStyle=wash;ctx.fillRect(0,0,1480,320);
      // One continuous lower rail, a lift on the right and an upper return pipe.
      line([[58,284],[1390,284],[1410,270],[1410,34],[1390,14],[72,14]],'#050d14',12);
      line([[58,284],[1390,284],[1410,270],[1410,34],[1390,14],[72,14]],'#8d6f4580',4);
      line([[58,263],[1370,263],[1370,47],[72,47]],'#50778670',3);
      rounded(1367,47,45,215,20,'#24444b33','#80bcc93b');
      [132,278,490,748,1004,1218,1388].forEach(x=>{line([[x,286],[x,304]],'#52616b',5);rounded(x-14,302,28,6,3,'#1f303c','#405563')});
      // Reserve hopper also makes the changing number of balls visible.
      rounded(60,94,170,118,16,'#19313988','#7199a94f');
      rounded(54,207,182,13,5,'#34404a','#a0927266');
      label('KUGELWERK',145,76,22,'#ddcca2','center');
      label('HH : MM',145,244,17,'#9cb3bd','center');
      chambers.forEach((x,i)=>{
        const glass=ctx.createLinearGradient(x,0,x+176,0);glass.addColorStop(0,'#c3e4e716');glass.addColorStop(.12,'#72a0af09');glass.addColorStop(.85,'#24464a22');glass.addColorStop(1,'#c3e4e71c');
        rounded(x,49,176,184,19,glass,'#b4d2d557');
        rounded(x-5,225,186,11,4,'#39444b','#b1a0787a');
        for(const bolt of [x+9,x+166]){ctx.fillStyle='#aa9670';ctx.beginPath();ctx.arc(bolt,231,2.5,0,Math.PI*2);ctx.fill()}

      });
      // Foreground highlights keep the moving balls visually inside glass.
      chambers.forEach(x=>{line([[x+10,78],[x+10,190]],'#d2f5ff32',3);line([[x+17,63],[x+60,58]],'#e7ffff30',2)});
      const small=false;
      if(!small){label('STUNDEN',520,257,15,'#a1b3bd','center');label('MINUTEN',1020,257,15,'#a1b3bd','center');label('RÜCKLAUF',1267,244,15,'#8ea9b4','center');}
    }

  function ensureScene(){
    if(background)return;
    makeSprite();background=document.createElement('canvas');background.width=1480;background.height=320;
    const displayContext=ctx;ctx=background.getContext('2d');drawScene();ctx=displayContext;
  }
  function draw(t=null){
    ensureScene();ctx.drawImage(background,0,0);
    chambers.forEach(x=>{
      const open=t!==null&&t>.02&&t<.8;
      ctx.save();ctx.translate(x+18,238);ctx.rotate(open ? .22 : 0);
      rounded(0,0,140,5,2,'#a38d5c');ctx.restore();
    });
    ball({x:740,y:112,r:7});ball({x:740,y:169,r:7});
    if(t===null)from.forEach(ball);else from.forEach((_,i)=>ball(position(i,t)));
    chambers.forEach(x=>{line([[x+10,78],[x+10,190]],'#d2f5ff32',3);line([[x+17,63],[x+60,58]],'#e7ffff30',2)});
    if(ampm)label(ampm,740,216,22,'#dcc799','center');
    canvas.dataset.drawCount=String(Number(canvas.dataset.drawCount||0)+1);
  }
  function stop(){
    if(frameId!==null)cancelAnimationFrame(frameId);
    frameId=null;if(to.length)from=to;canvas.dataset.animating='false';
  }
  function visible(){return element.isConnected&&element.classList.contains('screen-active')&&document.visibilityState!=='hidden';}
  function tick(timestamp){
    if(!visible()||globalThis.matchMedia?.('(prefers-reduced-motion: reduce)').matches){stop();needsDraw=true;return;}
    if(timestamp-lastFrame<1000/24){frameId=requestAnimationFrame(tick);return;}
    lastFrame=timestamp;
    const progress=clamp((timestamp-started)/5000);
    draw(progress);
    if(progress>=1){stop();draw();}else frameId=requestAnimationFrame(tick);
  }
  let needsDraw=true;
  function update(currentSettings=settings,now=new Date(),allowMotion=true){
    if(!visible()){stop();needsDraw=true;return;}
    const parts=clockDisplayParts(now,currentSettings),key=parts.hh+parts.mm;
    const changed=key!==lastKey||lastFormat!==parts.twelve;
    const animate=changed&&allowMotion&&lastKey!==null&&lastFormat===parts.twelve
      &&clockLedShouldRefresh(lastNow,now.getTime())
      &&!globalThis.matchMedia?.('(prefers-reduced-motion: reduce)').matches;
    lastNow=now.getTime();lastFormat=parts.twelve;ampm=parts.ampm;
    if(!changed&&!needsDraw)return;
    stop();
    to=marbleClockTargets(key);
    if(!from.length||!animate)from=to;
    lastKey=key;needsDraw=false;
    canvas.setAttribute('aria-label',`${parts.hh}:${parts.mm} ${parts.ampm}`.trim());
    canvas.dataset.time=key;
    if(animate){
      started=performance.now();lastFrame=-Infinity;canvas.dataset.animating='true';
      draw(0);frameId=requestAnimationFrame(tick);
    }else draw();
  }
  return {element,isClock:true,
    onMount(){needsDraw=true;update(settings,new Date(),false);},
    onUnmount(){stop();needsDraw=true;},
    onTick(_status,currentSettings,now){update(currentSettings,now);}
  };
}
