(() => {
  const $ = id => document.getElementById(id);
  const embedded = new URLSearchParams(location.search).get("embedded") === "1";
  let active = !embedded, prepared = null;
  if (embedded) document.body.classList.add("embedded");
  const reportReady = available => {
    if (embedded) parent.postMessage({type:"camper-journey-state", available}, location.origin);
  };
  window.addEventListener("message", event => {
    if (!embedded || event.origin !== location.origin || event.source !== parent
        || event.data?.type !== "camper-journey-active") return;
    active = event.data.active === true;
    if (active && prepared) render(prepared);
  });
  const number = value => Number.isFinite(value) ? value.toLocaleString("de-DE",{maximumFractionDigits:1}) : "–";
  const duration = seconds => {if (!Number.isFinite(seconds)) return "–";const minutes=Math.round(seconds/60);return `${Math.floor(minutes/60)} h ${String(minutes%60).padStart(2,"0")}`;};
  const day = date => `${date.getFullYear()}-${String(date.getMonth()+1).padStart(2,"0")}-${String(date.getDate()).padStart(2,"0")}`;
  const dateTime = value => new Date(value).toLocaleString("de-DE", {day:"2-digit",month:"2-digit",year:"numeric",hour:"2-digit",minute:"2-digit"});
  let mode="last",map=null,layers=null,failedTiles=0,loadedTiles=0;
  let requestSerial=0,pollTimer=null,renderedKey=null,renderedVersion=null;
  function resize(){const scale=$("display-frame").clientWidth/1480;$("display").style.transform=`scale(${scale})`;$("display-frame").style.height=`${320*scale}px`;}
  new ResizeObserver(resize).observe($("display-frame"));resize();
  function ensureMap(){
    if(map || !window.L)return;
    map=L.map("journey-map",{zoomControl:false,attributionControl:true,zoomAnimation:false,fadeAnimation:false,markerZoomAnimation:false,preferCanvas:true});
    map.attributionControl.setPrefix(false);
    const tiles=L.tileLayer("https://tile.openstreetmap.org/{z}/{x}/{y}.png",{maxZoom:18,attribution:'© <a href="https://www.openstreetmap.org/copyright" target="_blank" rel="noopener">OpenStreetMap</a> contributors'});
    tiles.on("tileerror",()=>{failedTiles++;if(!loadedTiles){$("map-message").hidden=false;$("map-message").textContent="Kartenhintergrund nicht verfügbar · Strecke bleibt sichtbar";}});
    tiles.on("tileload",()=>{loadedTiles++;if($("map-message").textContent.startsWith("Kartenhintergrund"))$("map-message").hidden=true;});
    tiles.addTo(map);layers=L.layerGroup().addTo(map);
  }
  function blank(text){for(const id of ["distance","drive","pause","stops"])$(id).textContent="–";$("trip-count").textContent="";$("device-name").textContent="TRACCAR";$("journey-source").textContent="";$("map-message").hidden=false;$("map-message").textContent=text;if(layers)layers.clearLayers();$("journey-date").textContent="";$("journey-map").style.visibility="hidden";}
  function render(data){
    if(data.empty){blank(data.message);return;}
    $("distance").textContent=number(data.distance_km);$("drive").textContent=duration(data.drive_seconds);$("pause").textContent=duration(data.pause_seconds);$("stops").textContent=number(data.stop_count);
    if(data.stops.some(stop=>stop.estimated))$("pause").textContent="ca. "+duration(data.pause_seconds);
    $("journey-source").textContent=data.unknown_seconds?`GPS-LÜCKE · ${Math.round(data.unknown_seconds/60)} MIN`:"TRACCAR · GPS";
    $("device-name").textContent=data.device_name;
    $("journey-date").textContent=dateTime(data.from)+" – "+dateTime(data.to);
    $("trip-count").textContent=`${data.trip_count} ${data.trip_count===1?"Fahrt":"Fahrten"}`;
    const points=data.segments.flat();
    if(!window.L || !points.length){$("map-message").hidden=false;$("map-message").textContent=points.length?"Kartenbibliothek nicht verfügbar":"Keine gültige Route verfügbar";return;}
    ensureMap();layers.clearLayers();$("journey-map").style.visibility="visible";
    for(const segment of data.segments)L.polyline(segment,{color:"#157963",weight:7,opacity:.85}).addTo(layers);
    for(const segment of data.segments)L.polyline(segment,{color:"#54edc4",weight:3,opacity:1}).addTo(layers);
    for(const stop of data.stops){const text=document.createElement("span");text.textContent="Stopp · "+(stop.estimated?"ca. ":"")+duration(stop.seconds);L.circleMarker([stop.latitude,stop.longitude],{radius:7,color:"#574327",weight:2,fillColor:"#ffe7a6",fillOpacity:1}).bindTooltip(text).addTo(layers);}
    const marker=(point,end,text)=>{const content=document.createElement("span");content.textContent=text;L.marker(point,{icon:L.divIcon({className:"",html:`<div class="route-marker${end?" end":""}"></div>`,iconSize:[20,20],iconAnchor:[10,10]}),title:end?"Ziel":"Start"}).bindTooltip(content).addTo(layers);};
    marker(points[0],false,data.start_address);marker(points.at(-1),true,data.end_address);
    map.invalidateSize({animate:false});map.fitBounds(L.latLngBounds(points),{paddingTopLeft:[35,120],paddingBottomRight:[35,50],maxZoom:15,animate:false});
    $("map-message").hidden=true;
  }
  function selection(){
    const payload={mode};
    if(mode==="vacation"){
      const a=new Date($("from").value+"T00:00:00"),b=new Date($("to").value+"T00:00:00");
      b.setDate(b.getDate()+1);payload.from=a.toISOString();payload.to=b.toISOString();
    }
    return payload;
  }
  async function load(refresh=false){
    const serial=++requestSerial;clearTimeout(pollTimer);
    try{
      const payload=selection(),key=JSON.stringify(payload);
      const response=await fetch("/api/traccar/journey",{method:"POST",headers:{"Content-Type":"application/json"},body:JSON.stringify({...payload,refresh}),cache:"no-store",signal:AbortSignal.timeout(5000)});
      const state=await response.json();if(serial!==requestSerial)return;
      if(!response.ok)throw new Error(state.detail||"Datenstand nicht verfügbar.");
      if(state.ready && state.data){
        const data=state.data,version=String(state.version)+data.loaded_at;
        prepared=data;reportReady(!data.empty);
        if(active && (renderedKey!==key || renderedVersion!==version)){render(data);renderedKey=key;renderedVersion=version;}
        $("status").textContent=data.empty?data.message:`Stand ${new Date(data.loaded_at).toLocaleTimeString("de-DE")} · ${state.loading?"wird im Hintergrund aktualisiert · ":""}${data.metrics_source||"GPS-Auswertung"}${data.warnings.length?" · "+data.warnings.join(" "):""}`;
      }else{
        prepared=null;reportReady(false);
        blank(state.state==="loading"?"Wird im Hintergrund vorbereitet …":state.message);
        renderedKey=null;renderedVersion=null;$("status").textContent=state.message;
      }
    }catch(error){
      if(serial!==requestSerial)return;
      prepared=null;reportReady(false);
      const text=error instanceof RangeError?"Bitte gültige Datumswerte auswählen.":error instanceof TypeError || error.name==="TimeoutError"?"Lokaler Datenstand derzeit nicht erreichbar.":error.message;
      blank(text);renderedKey=null;renderedVersion=null;$("status").textContent=text;
    }finally{
      if(serial===requestSerial && !document.hidden)pollTimer=setTimeout(()=>load(),embedded?5000:2000);
    }
  }
  document.querySelectorAll("[data-mode]").forEach(button=>button.addEventListener("click",()=>{mode=button.dataset.mode;document.querySelectorAll("[data-mode]").forEach(b=>b.setAttribute("aria-pressed",String(b===button)));$("vacation-controls").hidden=mode!=="vacation";load();}));
  $("refresh").addEventListener("click",()=>load(true));$("load-period").addEventListener("click",()=>load());
  document.addEventListener("visibilitychange",()=>{if(document.hidden)clearTimeout(pollTimer);else load();});
  let saved=[];
  $("vacation").addEventListener("change",()=>{const item=saved[Number($("vacation").value)];if($("vacation").value!==""&&item){$("from").value=item.start;$("to").value=item.end;load();}});
  const today=new Date(),first=new Date();first.setDate(today.getDate()-6);$("from").value=day(first);$("to").value=day(today);
  if (!embedded) fetch("/api/traccar/vacations",{cache:"no-store"}).then(r=>r.json()).then(data=>{saved=data.vacations||[];saved.forEach((v,i)=>$("vacation").add(new Option(`${v.name} · ${v.start} – ${v.end}`,String(i))));const active=saved.findIndex(v=>v.start<=day(today)&&v.end>=day(today));if(active>=0){$("vacation").value=String(active);$("from").value=saved[active].start;$("to").value=saved[active].end;if(mode==="vacation")load();}}).catch(()=>{});
  load();
})();
