// Reproducible public demo: production renderers, no private API or user settings.
const demoSettings = {
  time_format_24h:true, theme:"flip", theme_background_colors:{},
  vacations:[{id:"demo",name:"Beispielreise",destination:"Berge & Seen",
    start_date:"2026-09-07",end_date:"2026-09-21",enabled:true}],
};
const demoNow = new Date(2026, 8, 10, 18, 12, 0);
const demoStatus = {
  server_time_iso:"2026-09-10T18:12:00+02:00",
  weather:{available:true,location_name:"Beispielort · Deutschland",unit_celsius:true,
    temperature:23,apparent_temperature:24,wind_speed:9,condition_code:2,
    sunrise:"2026-09-10T06:43:00+02:00",sunset:"2026-09-10T19:36:00+02:00",
    daylight_duration_seconds:46380,
    forecast:[0,1,2,3].map(i=>({date:`2026-09-${10+i}`,condition_code:[2,0,61,2][i],
      temp_max:[25,27,21,23][i],temp_min:[14,15,13,12][i],
      precipitation_probability:[15,5,75,20][i],precipitation_sum:[0.2,0,5.8,0.4][i]}))},
  moon:{phase_name:"Neumond",illumination_pct:1,phase_fraction:.974,
    moonrise:"2026-09-10T05:41:00+02:00",moonset:"2026-09-10T19:13:00+02:00"},
};
const demoFactories = {
  panorama:()=>createPanoramaClockScreen(demoSettings),
  led:()=>createLedClockScreen(demoSettings),
  flip:()=>createClockScreen(demoSettings,"flip"),
  weather:createWeatherScreen,
  sun:createSunScreen,
  calendar:createCalendarScreen,
  photos:()=>createPhotoFrameScreen({fetcher:null,intervalMs:86400000,initialPhotos:[
    {id:"demo-1",url:"assets/photo-demo/portrait-a.jpg",aspect_ratio:.67,place:"Beispielmotiv · Berge"},
    {id:"demo-2",url:"assets/photo-demo/portrait-b.jpg",aspect_ratio:.75,place:"Beispielmotiv · See"},
    {id:"demo-3",url:"assets/photo-demo/portrait-c.jpg",aspect_ratio:.8,place:"Beispielmotiv · Abendlicht"},
  ]}),
};
const demoName = new URLSearchParams(location.search).get("screen") || "panorama";
const demoScreen = (demoFactories[demoName] || demoFactories.panorama)();
document.getElementById("screens").appendChild(demoScreen.element);
demoScreen.element.classList.add("screen-active");
demoScreen.onMount?.();
demoScreen.onTick?.(demoStatus,demoSettings,demoNow);
document.title = `Camper-Display · ${demoName} · Beispieldaten`;
function fitDemo() {
  document.getElementById("stage").style.transform = `scale(${Math.min(innerWidth/1480,innerHeight/320)})`;
}
addEventListener("resize",fitDemo);
fitDemo();
