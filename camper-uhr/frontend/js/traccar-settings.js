(() => {
  const root = document.getElementById("traccar-settings");
  if (!root) return;
  root.innerHTML = `<fieldset>
    <legend>Traccar · Fahrdaten</legend>
    <label for="traccar-url">API-Adresse</label>
    <input id="traccar-url" type="text" style="width:100%" maxlength="2048" spellcheck="false" placeholder="https://traccar.example.org/api">
    <label for="traccar-token">Zugriffstoken für CamperDisplay</label>
    <input id="traccar-token" type="password" style="width:100%" maxlength="8192" autocomplete="off" spellcheck="false" placeholder="Token hier einfügen">
    <p class="hint" id="traccar-secret-state">Token wird nicht zurück an den Browser übertragen.</p>
    <label for="traccar-device">Fahrzeug</label>
    <select id="traccar-device"><option value="">Zuerst Verbindung testen</option></select>
    <div><button type="button" id="traccar-test">Verbindung testen</button><button type="button" id="traccar-save">Traccar speichern</button><button type="button" id="traccar-clear">Gespeicherten Token entfernen</button></div>
    <p id="traccar-status" role="status" aria-live="polite">Einstellungen werden geladen …</p>
    <p class="hint">Testen speichert nichts. Nach erfolgreichem Test Fahrzeug wählen und „Traccar speichern“ drücken. Traccar wird getrennt von den übrigen Einstellungen gespeichert.</p>
    <p class="hint">Nur Lesezugriff. Der Token bleibt in einer separaten lokalen Datenbank, unverschlüsselt auf dem Datenträger; nicht im Browser-Speicher und nicht in der Kiosk-Konfiguration. HTTP bitte nur im vertrauenswürdigen Heimnetz bzw. über das bestehende VPN verwenden. Nach Speicherung von Token und Fahrzeug werden Fahrdaten alle 5 Minuten im Hintergrund vorbereitet, solange der Dienst läuft.</p>
  </fieldset>`;
  const el = (id) => document.getElementById(`traccar-${id}`);
  let loaded = false;
  const controls = [...root.querySelectorAll("input,select,button")];
  const busy = (value) => controls.forEach(c => { c.disabled = value; });
  const message = (text) => { el("status").textContent = text; };
  const payload = () => ({api_url:el("url").value.trim(),token:el("token").value.trim(),device_id:el("device").value ? Number(el("device").value) : null});
  async function api(path, method="GET", data) {
    const response = await fetch(`/api/traccar/${path}`, {
      method, cache:"no-store", headers: data ? {"Content-Type":"application/json"} : {},
      body: data ? JSON.stringify(data) : undefined, signal:AbortSignal.timeout(25000),
    });
    const result = await response.json();
    if (!response.ok) throw new Error(typeof result.detail === "string" ? result.detail : "Verbindung fehlgeschlagen.");
    return result;
  }
  function secretState(config) {
    el("token").placeholder = config.token_saved ? "Gespeichert – leer lassen zum Beibehalten" : "Token hier einfügen";
    el("secret-state").textContent = config.token_saved ? "Token gespeichert. Bei anderer API-Adresse bitte den passenden Token erneut eingeben." : "Noch kein Token gespeichert.";
    el("clear").hidden = !config.token_saved;
  }
  function devices(items, selected) {
    el("device").replaceChildren(new Option("Fahrzeug auswählen", ""));
    for (const item of items) el("device").add(new Option(item.name, String(item.id)));
    el("device").value = selected ? String(selected) : "";
  }
  async function action(fn) {
    if (!loaded) return;
    busy(true);
    try { await fn(); } catch (error) {
      message(error.name === "TimeoutError" ? "Zeitüberschreitung. Netzwerk und API-Adresse prüfen." : (error instanceof TypeError ? "Lokaler Dienst nicht erreichbar." : error.message));
    } finally { busy(false); }
  }
  el("test").addEventListener("click", () => action(async () => {
    message("Prüfe API-Zugriff, Fahrzeuge und letzte Position …");
    const result = await api("test", "POST", payload());
    devices(result.devices, result.device_id);
    let text = result.message;
    text += "\nKontorechte werden hier nicht geprüft: In Traccar bitte Admin aus und Read-only an lassen.";
    if (result.position) {
      const p = result.position;
      const date = new Date(p.fix_time);
      text += `\nLetzte Position: ${Number.isFinite(date.getTime()) ? date.toLocaleString("de-DE") : "Zeit unbekannt"}`;
      text += p.stale ? " · VERALTET / NICHT GÜLTIG – keine aktuellen Fahrwerte" : " · aktuell";
      if (!p.stale) text += `\nGeschwindigkeit: ${p.speed_kmh ?? "–"} km/h · Höhe: ${p.altitude_m ?? "–"} m`;
    } else if (result.device_id) text += "\nFür das Fahrzeug liegt noch keine Position vor.";
    message(text);
  }));
  el("save").addEventListener("click", () => action(async () => {
    const config = await api("settings", "PUT", payload());
    el("token").value = "";
    el("url").value = config.api_url;
    secretState(config);
    message(location.hostname === "127.0.0.1" ? "Traccar-Einstellungen auf diesem Rechner gespeichert. Der Pi wurde nicht geändert." : "Traccar-Einstellungen gespeichert.");
  }));
  el("clear").addEventListener("click", () => action(async () => {
    if (!confirm("Gespeicherten Traccar-Token aus dieser Installation entfernen? Der Token auf dem Server bleibt gültig.")) return;
    const config = await api("settings", "PUT", {...payload(),token:"",clear_token:true});
    el("token").value = "";
    secretState(config);
    message("Lokaler Token entfernt. Zum Widerrufen bitte Traccar verwenden.");
  }));
  el("url").addEventListener("input", () => devices([], null));
  el("token").addEventListener("input", () => devices([], null));
  busy(true);
  api("settings").then(config => {
    el("url").value = config.api_url;
    secretState(config);
    if (config.device_id) devices([{id:config.device_id,name:`Gespeichertes Fahrzeug · ${config.device_id}`}], config.device_id);
    message("Bereit. Token einfügen und Verbindung testen.");
    loaded = true;
    busy(false);
  }).catch(() => message("Lokaler Traccar-Dienst nicht erreichbar. Bitte die Seite über den Einrichtungsserver öffnen."));
})();
