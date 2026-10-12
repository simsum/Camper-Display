(function loadOptionalMapLibrary() {
  const stylesheet = document.createElement("link");
  stylesheet.rel = "stylesheet";
  stylesheet.href = "https://unpkg.com/leaflet@1.9.4/dist/leaflet.css";
  document.head.appendChild(stylesheet);

  const script = document.createElement("script");
  script.src = "https://unpkg.com/leaflet@1.9.4/dist/leaflet.js";
  script.async = true;
  script.onload = () => window.dispatchEvent(new Event("camper:leaflet-ready"));
  document.head.appendChild(script);
})();

// Load WebGL only when the map is actually shown. Journey keeps using Leaflet.
window.loadNavigationMap = (() => {
  let pending;
  return () => {
    if (window.maplibregl) return Promise.resolve(window.maplibregl);
    if (pending) return pending;
    pending = new Promise((resolve, reject) => {
      const css = document.createElement('link');
      css.rel = 'stylesheet';
      css.href = 'https://unpkg.com/maplibre-gl@5.6.0/dist/maplibre-gl.css';
      document.head.appendChild(css);
      const script = document.createElement('script');
      script.src = 'https://unpkg.com/maplibre-gl@5.6.0/dist/maplibre-gl.js';
      script.async = true;
      const timeout = setTimeout(() => reject(new Error('Kartenbibliothek nicht erreichbar')), 12000);
      script.onload = () => { clearTimeout(timeout); resolve(window.maplibregl); };
      script.onerror = () => { clearTimeout(timeout); reject(new Error('Kartenbibliothek nicht erreichbar')); };
      document.head.appendChild(script);
    });
    return pending;
  };
})();
