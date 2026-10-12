function createArrivalScreen(data) {
  const element=document.createElement('div');element.className='screen arrival-screen';
  // Remote text is never interpreted as markup.
  element.innerHTML='<img class="arrival-photo" alt=""><div class="arrival-shade"></div><div class="arrival-copy"><div class="arrival-welcome"><div class="arrival-eyebrow">ANGEKOMMEN IN</div><h1></h1><div class="arrival-region"></div><div class="arrival-travel"></div></div><div class="arrival-story"><p></p><div class="arrival-facts"></div></div></div><div class="arrival-credits"></div>';
  const q=s=>element.querySelector(s);
  q('h1').textContent=data.place||'Eurem Standort';
  q('h1').style.fontSize=Math.max(44,Math.min(104,780/(data.place||'').length))+'px';
  q('.arrival-region').textContent=data.region||'';
  q('.arrival-story p').textContent=data.extract||'Willkommen am neuen Standort.';
  function fact(parent,label,value){const item=document.createElement('div'),v=document.createElement('strong'),l=document.createElement('span');v.textContent=value;l.textContent=label;item.append(v,l);parent.appendChild(item);}
  if(Number.isFinite(data.altitude_m))fact(q('.arrival-travel'),data.altitude_label||'Höhe',Math.round(data.altitude_m)+' m');
  if(/^\d{4}-\d\d-\d\dT\d\d:\d\d/.test(data.sunset||''))fact(q('.arrival-travel'),'Sonnenuntergang',data.sunset.slice(11,16));
  (data.facts||[]).slice(0,2).forEach(f=>fact(q('.arrival-facts'),f.label,f.value));
  const photo=q('.arrival-photo');
  const source=data.image_url||'';
  if(/^\/api\/arrival\/image\/[a-f0-9]+$/.test(source)||/^data:image\/(jpeg|png);base64,/.test(source)){
    photo.src=source;photo.alt='Ortsansicht '+(data.place||'');
    photo.onerror=()=>{photo.style.display='none';};
  }else photo.style.display='none';
  const credits=q('.arrival-credits');
  function link(label,url){const a=document.createElement('a');a.textContent=label;if(/^https:\/\/(?:de|it|en)\.wikipedia\.org\//.test(url)||/^https:\/\/(?:commons\.wikimedia\.org|creativecommons\.org|www\.openstreetmap\.org)\//.test(url)){a.href=url;a.target='_blank';a.rel='noopener noreferrer';}credits.appendChild(a);}
  if(data.wiki_url){link('Wikipedia · gekürzt',data.wiki_url);link('CC BY-SA 4.0','https://creativecommons.org/licenses/by-sa/4.0/');}
  if(data.image_credit){link(data.image_credit,data.image_source);if(data.image_license_url)link('Bildlizenz',data.image_license_url);}
  if(data.source_credit)link('Ort: © OpenStreetMap','https://www.openstreetmap.org/copyright');
  if(data.test){const label=document.createElement('span');label.textContent='TESTORT';credits.appendChild(label);}
  return {element,onMount(){},onUnmount(){}};
}
