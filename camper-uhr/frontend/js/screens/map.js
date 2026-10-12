function createMapScreen() {
  const el = document.createElement("div");
  el.className = "screen map-screen";
  el.innerHTML = `
    <div class="map-layout">
      <div class="map-pane">
        <div class="map-container" id="map"></div>
        <div class="map-offline" id="map-offline">
          <div class="map-offline-icon">⌖</div>
          <div class="map-offline-title">Karte wird geladen</div>
          <div class="map-offline-copy">GPS bleibt unabhängig davon aktiv</div>
        </div>
      </div>
      <aside class="map-telemetry" aria-label="Aktuelle Fahrdaten">
        <div class="map-metric map-metric-speed">
          <div class="map-metric-label">Geschwindigkeit</div>
          <div class="map-metric-value-row">
            <span class="map-metric-value" id="map-speed">–</span>
            <span class="map-metric-unit">km/h</span>
          </div>
        </div>
        <div class="map-metric map-metric-altitude">
          <div class="map-metric-label">Höhe</div>
          <div class="map-metric-value-row">
            <span class="map-metric-value" id="map-altitude">–</span>
            <span class="map-metric-unit">m</span>
          </div>
          <div class="map-altitude-reference" id="map-altitude-reference">GPS</div>
        </div>
      </aside>
    </div>
  `;

  const container = el.querySelector("#map");
  const overlay = el.querySelector("#map-offline");
  const title = el.querySelector(".map-offline-title");
  const badge = document.createElement("div");
  badge.className = "map-navigation-label";
  el.querySelector(".map-pane").appendChild(badge);
  let map = null, marker = null, trailLine = null;
  let active = false, generation = 0, ready = false, fallback = false, fallbackRequested = false;
  let latest = null, lastCamera = null, lastTrailFetch = 0, trailAbort = null;
  let navigation = createMapNavigation();

  function message(text) {
    title.textContent = text;
    overlay.style.display = "flex";
  }

  function disposeMap() {
    if (trailAbort) trailAbort.abort();
    trailAbort = null;
    if (map) map.remove();
    map = marker = trailLine = null;
    ready = false;
    lastCamera = null;
    lastTrailFetch = 0;
  }

  function startFallback() {
    if (!active || !window.L || map) return;
    fallback = true;
    map = window.L.map(container, {zoomControl: false, attributionControl: true});
    const tiles = window.L.tileLayer("https://tile.openstreetmap.org/{z}/{x}/{y}.png", {
      maxZoom: 19,
      attribution: '&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a>',
    }).addTo(map);
    tiles.on("tileerror", () => { if (active) badge.textContent = "2D · Kartenverbindung unterbrochen"; });
    ready = true;
    if (latest) update(...latest);
  }

  function fallbackReady() { if (fallbackRequested) startFallback(); }

  function startMap(lib, token) {
    if (!active || token !== generation) return;
    try {
      map = new lib.Map({
        container, interactive: false, attributionControl: false,
        center: [0, 0], zoom: 13, maxZoom: 19, maxPitch: 50,
        fadeDuration: 0, renderWorldCopies: false, maxTileCacheSize: 64,
        pixelRatio: 1,
        style: {
          version: 8,
          sources: {osm: {type: "raster", tiles: ["https://tile.openstreetmap.org/{z}/{x}/{y}.png"], tileSize: 256, maxzoom: 19,
            attribution: '&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a>'}},
          layers: [{id: "osm", type: "raster", source: "osm", paint: {"raster-fade-duration": 0}}],
        },
      });
      map.addControl(new lib.AttributionControl({compact: false}), "bottom-right");
      map.on("load", () => {
        if (!active || token !== generation) return;
        ready = true;
        map.addSource("trail", {type: "geojson", data: emptyTrail()});
        map.addLayer({id: "trail", type: "line", source: "trail", paint: {"line-color": "#168eae", "line-width": 4}});
        if (latest) update(...latest);
      });
      map.on("error", () => { if (active) badge.textContent = "Kartenverbindung unterbrochen"; });
      map.on("webglcontextlost", () => {
        if (!active || token !== generation) return;
        disposeMap();
        fallbackRequested = true;
        startFallback();
      });
    } catch (_) {
      disposeMap();
      fallbackRequested = true;
      startFallback();
      if (!map) message("3D nicht verfügbar · 2D-Karte wird geladen");
    }
  }

  function emptyTrail(points = []) {
    return {type: "FeatureCollection", features: points.length < 2 ? [] : [{type: "Feature", properties: {},
      geometry: {type: "LineString", coordinates: points.map(p => [p.longitude, p.latitude])}}]};
  }

  function refreshTrail(settings) {
    if (!settings.map_trail_enabled) {
      if (fallback && trailLine) trailLine.setLatLngs([]);
      if (!fallback) map.getSource("trail")?.setData(emptyTrail());
      if (trailAbort) trailAbort.abort();
      return;
    }
    if (trailAbort || Date.now() - lastTrailFetch < 20000) return;
    lastTrailFetch = Date.now();
    const token = generation;
    const controller = new AbortController();
    trailAbort = controller;
    fetch("/api/gps/trail", {signal: controller.signal}).then(r => {
      if (!r.ok) throw new Error("trail");
      return r.json();
    }).then(points => {
      if (!active || token !== generation || controller.signal.aborted) return;
      if (fallback) {
        const coords = points.map(p => [p.latitude, p.longitude]);
        if (!trailLine) trailLine = window.L.polyline(coords, {color: "#168eae", weight: 4}).addTo(map);
        else trailLine.setLatLngs(coords);
      } else map.getSource("trail")?.setData(emptyTrail(points));
    }).catch(() => {}).finally(() => { if (trailAbort === controller) trailAbort = null; });
  }

  function update(status, settings) {
    latest = [status, settings];
    if (!active) return;
    const gps = status.gps;
    el.querySelector("#map-speed").textContent = gps.connected && Number.isFinite(gps.speed_kmh) ? String(Math.max(0, Math.round(gps.speed_kmh))) : "–";
    el.querySelector("#map-altitude").textContent = gps.connected && Number.isFinite(gps.altitude_m) ? String(Math.round(gps.altitude_m)) : "–";
    el.querySelector("#map-altitude-reference").textContent = gps.altitude_reference === "msl" ? "ü. NN" : "GPS";
    const camera = navigation(status, settings);
    if (!camera) { message("Kein GPS-Signal"); return; }
    if (!map || !ready) return;
    overlay.style.display = "none";
    badge.textContent = gps.simulation_active ? "SIMULATION" : "";
    badge.hidden = !gps.simulation_active;
    const key = JSON.stringify(camera);
    if (key !== lastCamera) {
      if (fallback) {
        const pos = [gps.latitude, gps.longitude];
        map.setView(pos, camera.zoom + 1, {animate: false});
        if (!marker) marker = window.L.circleMarker(pos, {radius: 9, color: "#fff", fillColor: "#ff8c3a", fillOpacity: 1}).addTo(map);
        else marker.setLatLng(pos);
      } else {
        // Immediate updates avoid repeated one-second camera animations on Pi 3.
        map.jumpTo(camera);
        if (!marker) {
          const arrow = document.createElement("div");
          arrow.className = "map-vehicle";
          marker = new window.maplibregl.Marker({element: arrow, rotationAlignment: "viewport", pitchAlignment: "viewport"}).setLngLat(camera.center).addTo(map);
        }
        marker.setLngLat(camera.center);
        marker.getElement().classList.toggle("map-vehicle-standing", camera.pitch === 0 || !camera.hasHeading);
      }
      lastCamera = key;
    }
    refreshTrail(settings);
  }

  return {
    element: el,
    onMount() {
      active = true;
      const token = ++generation;
      fallback = false;
      fallbackRequested = false;
      navigation = createMapNavigation();
      message("Karte wird geladen");
      window.addEventListener("camper:leaflet-ready", fallbackReady);
      window.loadNavigationMap().then(lib => startMap(lib, token)).catch(() => {
        if (!active || token !== generation) return;
        fallbackRequested = true;
        startFallback();
        if (!map) message("Kartenbibliothek nicht verfügbar");
      });
    },
    onTick: update,
    onUnmount() {
      active = false;
      ++generation;
      window.removeEventListener("camper:leaflet-ready", fallbackReady);
      disposeMap();
      latest = null;
    },
  };
}

// Stateful course handling is independent of the renderer and testable without WebGL.
function createMapNavigation() {
  let heading = null;
  let simulated = null;
  return (status, settings) => {
    const gps = status.gps;
    if (simulated !== gps.simulation_active) heading = null;
    simulated = gps.simulation_active;
    if (!gps.connected || !Number.isFinite(gps.latitude) || !Number.isFinite(gps.longitude)) {
      heading = null;
      return null;
    }
    const driving = status.operating?.mode === "drive";
    if (!driving) heading = null;
    else if (Number.isFinite(gps.speed_kmh) && gps.speed_kmh >= 3) {
      heading = Number.isFinite(gps.heading_deg) && gps.heading_deg >= 0 && gps.heading_deg < 360 ? gps.heading_deg : null;
    }
    const near = settings.map_zoom_near ?? 16;
    const far = settings.map_zoom_far ?? 11;
    const ratio = Math.max(0, Math.min(1, (gps.speed_kmh || 0) / (settings.map_zoom_speed_threshold_kmh || 80)));
    return {
      center: [gps.longitude, gps.latitude],
      zoom: near + (far - near) * ratio - 1, // MapLibre zoom uses 512px, Leaflet 256px.
      bearing: driving && heading !== null ? heading : 0,
      pitch: driving ? 45 : 0,
      padding: {top: driving ? 100 : 0, bottom: 0, left: 0, right: 0},
      hasHeading: heading !== null,
      label: driving ? (heading !== null ? "Fahrtrichtung oben" : "Richtung fehlt · Norden oben") : "Stand · Norden oben",
    };
  };
}
if (typeof module !== "undefined") module.exports = {createMapNavigation};
