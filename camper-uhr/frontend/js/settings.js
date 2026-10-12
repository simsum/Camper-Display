const SCREEN_LABELS = {
  clock_flip: "Uhr · Flip",
  clock_blue: "Uhr · Blau",
  clock_blank: "Uhr · Schlicht",
  clock_panorama: "Uhr · Panorama",
  clock_led: "Uhr · Bahnhofs-LED",
  clock_linear: "Uhr · Linear",
  clock_marble: "Uhr · Kugelbahn",
  journey: "Fahrten · Traccar (letzter Fahrtag · 24 h)",
  calendar: "Datum & Urlaub",
  weather: "Wetter",
  map: "Karte",
  sun: "Himmel",
};

let currentSettings = null;
let savedSnapshot = null;
let saving = false;

function settingsSnapshot() {
  const inputs = [...document.querySelectorAll('#settings-groups input, #settings-groups select')]
    .filter(input => !input.closest('#traccar-settings, #group-tests'))
    .map(input => [input.id, input.dataset.field || '', input.type === 'checkbox' ? input.checked : input.value]);
  return JSON.stringify([inputs, currentSettings?.screens, currentSettings?.vacations, currentSettings?.theme_background_colors]);
}
function refreshDirtyState() {
  if (savedSnapshot === null) return;
  const dirty = settingsSnapshot() !== savedSnapshot;
  document.body.dataset.unsaved = String(dirty);
  document.getElementById('dirty-state').textContent = saving ? 'Wird gespeichert …'
    : dirty ? 'Ungespeicherte Änderungen' : 'Alle Änderungen gespeichert';
  document.getElementById('save-btn').disabled = saving || !dirty;
}
function acceptSavedState() {
  savedSnapshot = settingsSnapshot();
  refreshDirtyState();
}
document.addEventListener('input', refreshDirtyState);
document.addEventListener('change', refreshDirtyState);
window.addEventListener('beforeunload', event => {
  if (savedSnapshot !== null && settingsSnapshot() !== savedSnapshot) {
    event.preventDefault();event.returnValue = '';
  }
});

function newVacationId() {
  return globalThis.crypto?.randomUUID?.()
    || `vacation-${Date.now()}-${Math.random().toString(16).slice(2)}`;
}

function localDateInputValue(date) {
  const year = date.getFullYear();
  const month = String(date.getMonth() + 1).padStart(2, "0");
  const day = String(date.getDate()).padStart(2, "0");
  return `${year}-${month}-${day}`;
}

function renderVacations() {
  const container = document.getElementById("vacation-settings-list");
  currentSettings.vacations ||= [];
  container.innerHTML = "";
  if (currentSettings.vacations.length === 0) {
    const empty = document.createElement("div");
    empty.className = "vacation-empty";
    empty.textContent = "Noch keine Urlaubszeit eingetragen.";
    container.appendChild(empty);
    return;
  }

  currentSettings.vacations.forEach((vacation, index) => {
    const row = document.createElement("div");
    row.className = "vacation-settings-row";
    row.innerHTML = `
      <input type="checkbox" data-field="enabled" title="In der Anzeige verwenden">
      <input type="text" data-field="name" maxlength="80" placeholder="Name, z. B. Herbsttour">
      <input type="text" data-field="destination" maxlength="120" placeholder="Zielort (optional)">
      <input type="date" data-field="start_date" title="Beginn">
      <input type="date" data-field="end_date" title="Ende">
      <button type="button" title="Urlaub löschen">Löschen</button>
    `;
    row.querySelectorAll("input[data-field]").forEach((input) => {
      const field = input.dataset.field;
      if (input.type === "checkbox") input.checked = Boolean(vacation[field]);
      else input.value = vacation[field] || "";
      input.addEventListener("input", () => {
        currentSettings.vacations[index][field] = input.type === "checkbox" ? input.checked : input.value;
      });
    });
    row.querySelector("button").addEventListener("click", () => {
      currentSettings.vacations.splice(index, 1);
      renderVacations();
      refreshDirtyState();
    });
    container.appendChild(row);
  });
}

function addVacation() {
  const start = new Date();
  start.setHours(0, 0, 0, 0);
  const end = new Date(start);
  end.setDate(end.getDate() + 7);
  currentSettings.vacations ||= [];
  currentSettings.vacations.push({
    id: newVacationId(),
    name: "Neuer Urlaub",
    destination: "",
    start_date: localDateInputValue(start),
    end_date: localDateInputValue(end),
    enabled: true,
  });
  renderVacations();
  refreshDirtyState();
}

function validateVacations() {
  for (const vacation of currentSettings.vacations || []) {
    if (!vacation.name.trim()) return "Bitte für jeden Urlaub einen Namen eingeben";
    if (!vacation.start_date || !vacation.end_date) return "Bitte Beginn und Ende vollständig eingeben";
    if (vacation.end_date < vacation.start_date) return `Das Ende von „${vacation.name}“ liegt vor dem Beginn`;
  }
  return null;
}

function renderScreenOrder() {
  const container = document.getElementById("screen-order");
  container.innerHTML = "";
  currentSettings.screens.forEach((config, index) => {
    const row = document.createElement("div");
    row.className = "screen-row";
    row.innerHTML = `
      <span class="name">${SCREEN_LABELS[config.id] ?? config.id}</span>
      <label class="mode-cell">
        <input type="checkbox" data-field="stand_enabled" data-index="${index}" ${config.stand_enabled ? "checked" : ""} />
        Stand
        <input class="duration" type="number" data-field="stand_duration_seconds" data-index="${index}" min="3" max="600" value="${config.stand_duration_seconds}" /> s
      </label>
      <label class="mode-cell">
        <input type="checkbox" data-field="drive_enabled" data-index="${index}" ${config.drive_enabled ? "checked" : ""} />
        Fahrt
        <input class="duration" type="number" data-field="drive_duration_seconds" data-index="${index}" min="3" max="600" value="${config.drive_duration_seconds}" /> s
      </label>
      <div class="order-buttons">
        <button data-action="up" data-index="${index}" type="button">↑</button>
        <button data-action="down" data-index="${index}" type="button">↓</button>
      </div>
    `;
    container.appendChild(row);
  });

  container.querySelectorAll("input[data-field]").forEach((input) => {
    input.addEventListener("change", () => {
      const index = Number(input.dataset.index);
      currentSettings.screens[index][input.dataset.field] =
        input.type === "checkbox" ? input.checked : Number(input.value);
    });
  });

  container.querySelectorAll("button[data-action]").forEach((button) => {
    button.addEventListener("click", () => {
      const index = Number(button.dataset.index);
      const target = button.dataset.action === "up" ? index - 1 : index + 1;
      if (target < 0 || target >= currentSettings.screens.length) return;
      [currentSettings.screens[index], currentSettings.screens[target]] =
        [currentSettings.screens[target], currentSettings.screens[index]];
      renderScreenOrder();
      refreshDirtyState();
    });
  });
}

function renderThemeGrid() {
  const container = document.getElementById("theme-grid");
  container.innerHTML = "";
  currentSettings.theme_background_colors ||= {};
  NIXIE_THEMES.forEach((theme) => {
    const option = document.createElement("div");
    option.className = "theme-option";
    const preview = themePreviewSrc(theme);
    const background = currentSettings.theme_background_colors[theme.id] || "#000000";
    option.innerHTML = `
      ${preview ? `<img src="${preview}" alt="${theme.label}" />` : '<div class="placeholder">5</div>'}
      <span class="label">${theme.label}</span>
      <input type="color" value="${background}" title="Hintergrundfarbe für dieses Theme" />
    `;
    const colorInput = option.querySelector('input[type="color"]');
    colorInput.addEventListener("click", (event) => event.stopPropagation());
    colorInput.addEventListener("input", () => {
      currentSettings.theme_background_colors[theme.id] = colorInput.value;
    });
    container.appendChild(option);
  });
}

function setValue(id, value) {
  document.getElementById(id).value = value;
}

function numberValue(id) {
  return Number(document.getElementById(id).value);
}

async function loadSettings() {
  const response = await fetch("/api/settings");
  if (!response.ok) throw new Error("Einstellungen konnten nicht geladen werden");
  currentSettings = await response.json();
  document.getElementById("calendar-enabled").checked = currentSettings.calendar_enabled ?? false;
  setValue("calendar-url", currentSettings.calendar_url || "");

  document.getElementById("time24").checked = currentSettings.time_format_24h;
  setValue("brightness-stand", currentSettings.brightness_stand);
  setValue("brightness-drive", currentSettings.brightness_drive);
  setValue("panel-opacity", currentSettings.panel_opacity_percent ?? 52);
  setValue("panel-blur", currentSettings.panel_blur_pixels ?? 0);
  setValue("gpsd-host", currentSettings.gpsd_host);
  setValue("gpsd-port", currentSettings.gpsd_port);
  setValue("drive-enter-speed", currentSettings.drive_enter_speed_kmh);
  setValue("drive-enter-seconds", currentSettings.drive_enter_seconds);
  setValue("stand-enter-speed", currentSettings.stand_enter_speed_kmh);
  setValue("stand-enter-seconds", currentSettings.stand_enter_seconds);
  setValue("gps-hold-seconds", currentSettings.gps_state_hold_seconds);
  document.getElementById("celsius").checked = currentSettings.weather_unit_celsius;
  setValue("map-zoom-near", currentSettings.map_zoom_near);
  setValue("map-zoom-far", currentSettings.map_zoom_far);
  setValue("map-zoom-threshold", currentSettings.map_zoom_speed_threshold_kmh);
  document.getElementById("map-trail-enabled").checked = currentSettings.map_trail_enabled;
  setValue("map-trail-hours", currentSettings.map_trail_max_hours);
  setValue("photo-frame-duration", currentSettings.photo_frame_manual_seconds ?? 300);
  document.getElementById("schedule-enabled").checked = currentSettings.display_schedule_enabled;
  setValue("off-time", currentSettings.display_off_time);
  setValue("on-time", currentSettings.display_on_time);
  setValue("night-behavior", currentSettings.night_behavior || "off");
  setValue("brightness-night", currentSettings.brightness_night ?? 5);
  setValue("night-color", currentSettings.night_color || "amber");
  setValue("night-wake-seconds", currentSettings.night_wake_seconds ?? 30);
  document.getElementById("arrival-enabled").checked = currentSettings.arrival_enabled !== false;
  setValue("arrival-wait", currentSettings.arrival_wait_seconds ?? (currentSettings.arrival_wait_minutes ?? 5) * 60);
  setValue("arrival-duration", currentSettings.arrival_duration_seconds ?? 30);
  document.getElementById("touch-wake-enabled").checked = currentSettings.touch_wake_enabled;
  setValue("touch-wake-hold", currentSettings.touch_wake_hold_seconds);
  renderScreenOrder();
  renderThemeGrid();
  renderVacations();
  acceptSavedState();
}

function showStatus(message, isError = false) {
  const element = document.getElementById("status-msg");
  element.textContent = message;
  element.style.color = isError ? "#f88" : "#8f8";
  setTimeout(() => { element.textContent = ""; }, 3000);
}

async function saveSettings() {
  if (!currentSettings || saving) return false;
  const invalid = [...document.querySelectorAll('#settings-groups input')]
    .find(input => !input.closest('#traccar-settings, #group-tests') && !input.checkValidity());
  if (invalid) {
    invalid.closest('details').open = true;
    invalid.focus();invalid.reportValidity();return false;
  }
  saving = true;refreshDirtyState();
  // No edits can race with a PUT response and silently get overwritten.
  const controls = [...document.querySelectorAll('#settings-groups input, #settings-groups select, #settings-groups button')]
    .filter(input => !input.closest('#traccar-settings, #group-tests'));
  const disabled = controls.map(control => control.disabled);
  controls.forEach(control => {control.disabled = true;});
  try { return await writeSettings(); }
  finally {
    controls.forEach((control,index) => {control.disabled = disabled[index];});
    saving = false;refreshDirtyState();
  }
}

async function writeSettings() {
  const vacationError = validateVacations();
  if (vacationError) {
    showStatus(vacationError, true);
    return false;
  }
  currentSettings.calendar_enabled = document.getElementById("calendar-enabled").checked;
  currentSettings.calendar_url = document.getElementById("calendar-url").value.trim();
  if (currentSettings.calendar_enabled && !currentSettings.calendar_url) {
    showStatus("Bitte zuerst den iCloud-Freigabelink eintragen", true);
    return false;
  }
  currentSettings.time_format_24h = document.getElementById("time24").checked;
  currentSettings.brightness_stand = numberValue("brightness-stand");
  currentSettings.brightness_drive = numberValue("brightness-drive");
  currentSettings.panel_opacity_percent = numberValue("panel-opacity");
  currentSettings.panel_blur_pixels = numberValue("panel-blur");
  currentSettings.gpsd_host = document.getElementById("gpsd-host").value;
  currentSettings.gpsd_port = numberValue("gpsd-port");
  currentSettings.drive_enter_speed_kmh = numberValue("drive-enter-speed");
  currentSettings.drive_enter_seconds = numberValue("drive-enter-seconds");
  currentSettings.stand_enter_speed_kmh = numberValue("stand-enter-speed");
  currentSettings.stand_enter_seconds = numberValue("stand-enter-seconds");
  currentSettings.gps_state_hold_seconds = numberValue("gps-hold-seconds");
  currentSettings.weather_unit_celsius = document.getElementById("celsius").checked;
  currentSettings.map_zoom_near = numberValue("map-zoom-near");
  currentSettings.map_zoom_far = numberValue("map-zoom-far");
  currentSettings.map_zoom_speed_threshold_kmh = numberValue("map-zoom-threshold");
  currentSettings.map_trail_enabled = document.getElementById("map-trail-enabled").checked;
  currentSettings.map_trail_max_hours = numberValue("map-trail-hours");
  currentSettings.photo_frame_manual_seconds = numberValue("photo-frame-duration");
  currentSettings.display_schedule_enabled = document.getElementById("schedule-enabled").checked;
  currentSettings.display_off_time = document.getElementById("off-time").value;
  currentSettings.display_on_time = document.getElementById("on-time").value;
  currentSettings.night_behavior = document.getElementById("night-behavior").value;
  currentSettings.brightness_night = numberValue("brightness-night");
  currentSettings.night_color = document.getElementById("night-color").value;
  currentSettings.night_wake_seconds = numberValue("night-wake-seconds");
  currentSettings.arrival_enabled = document.getElementById("arrival-enabled").checked;
  currentSettings.arrival_wait_seconds = numberValue("arrival-wait");
  delete currentSettings.arrival_wait_minutes;
  currentSettings.arrival_duration_seconds = numberValue("arrival-duration");
  currentSettings.touch_wake_enabled = document.getElementById("touch-wake-enabled").checked;
  currentSettings.touch_wake_hold_seconds = numberValue("touch-wake-hold");

  try {
    const response = await fetch("/api/settings", {
      method: "PUT",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(currentSettings),
    });
    if (!response.ok) {
      const body = await response.json().catch(() => ({}));
      const message = Array.isArray(body.detail) ? body.detail[0]?.msg : body.detail;
      throw new Error(message || "Einstellungen konnten nicht gespeichert werden");
    }
    currentSettings = await response.json();
    acceptSavedState();
    showStatus("Gespeichert");
    await updateCalendarStatus();
    return true;
  } catch (error) {
    showStatus(error.message || "Fehler beim Speichern", true);
    return false;
  }
}

async function updateCalendarStatus() {
  const statusEl = document.getElementById("calendar-sync-status");
  try {
    const response = await fetch("/api/calendar/status");
    if (!response.ok) throw new Error("Status nicht verfügbar");
    const state = await response.json();
    const trips = state.vacations || [];
    const labels = {
      disabled: "Kalenderanbindung ausgeschaltet.",
      loading: "Kalender wird geladen …",
      ready: `${trips.length} Urlaubstermine geladen.`,
      error: state.message || "Kalender konnte nicht aktualisiert werden.",
    };
    const last = state.last_success ? ` Letzter erfolgreicher Abruf: ${new Date(state.last_success).toLocaleString("de-DE")}.` : "";
    statusEl.textContent = (labels[state.state] || "Warte auf Kalender …") + last
      + (state.stale ? " Gespeicherter Stand wird weiterverwendet." : "");
    statusEl.style.color = state.state === "error" ? "#ffcb7b" : "#aaa";
    const list = document.getElementById("calendar-import-list");
    list.replaceChildren();
    const today = localDateInputValue(new Date());
    const upcoming = trips.filter((trip) => trip.end_date >= today);
    for (const trip of upcoming.slice(0, 8)) {
      const row = document.createElement("p");
      row.style.cssText = "font-size:14px;overflow-wrap:anywhere";
      row.textContent = `${trip.name} · ${trip.start_date.split("-").reverse().join(".")} – ${trip.end_date.split("-").reverse().join(".")}${trip.destination ? ` · ${trip.destination}` : ""}`;
      list.appendChild(row);
    }
    if (upcoming.length > 8) {
      const more = document.createElement("p");
      more.textContent = `… und ${upcoming.length - 8} weitere. Bearbeitung erfolgt im Apple-Kalender.`;
      list.appendChild(more);
    }
  } catch {
    statusEl.textContent = "Kalenderstatus momentan nicht erreichbar.";
  }
}

async function refreshCalendar() {
  const button = document.getElementById("calendar-refresh-btn");
  button.disabled = true;
  try {
    if (!await saveSettings()) return;
    const response = await fetch("/api/calendar/refresh", { method: "POST" });
    if (!response.ok) throw new Error();
    document.getElementById("calendar-sync-status").textContent = "Aktualisierung angefordert …";
  } catch {
    showStatus("Aktualisierung konnte nicht gestartet werden", true);
  } finally {
    button.disabled = false;
  }
}

async function simulatePosition() {
  const place_name = document.getElementById("sim-place").value;
  const speed_kmh = numberValue("sim-speed") || 0;
  const altitudeText = document.getElementById("sim-altitude").value.trim();
  const altitude_m = altitudeText === "" ? null : Number(altitudeText);
  const headingText = document.getElementById("sim-heading").value.trim();
  const heading_deg = headingText === "" ? null : Number(headingText);
  if (!place_name.trim()) {
    showStatus("Bitte einen Ort eingeben", true);
    return;
  }
  try {
    const response = await fetch("/api/debug/simulate-position", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ place_name, speed_kmh, altitude_m, heading_deg }),
    });
    if (!response.ok) {
      const body = await response.json().catch(() => ({}));
      throw new Error(body.detail || "Serverfehler");
    }
    showStatus("GPS-Position simuliert");
  } catch (error) {
    showStatus(error.message || "Fehler bei der Simulation", true);
  }
}

async function stopSimulation() {
  const response = await fetch("/api/debug/simulate-disconnect", { method: "POST" });
  showStatus(response.ok ? "Echtes GPS wieder aktiv" : "Fehler beim Beenden", !response.ok);
}

async function forceOperatingState(mode) {
  const response = await fetch("/api/debug/operating-state", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ mode }),
  });
  const labels = { auto: "Automatische Zustandserkennung", stand: "Stand erzwungen", drive: "Fahrt erzwungen" };
  showStatus(response.ok ? labels[mode] : "Zustand konnte nicht geändert werden", !response.ok);
}

async function setDisplayPower(on) {
  const response = await fetch(`/api/debug/display-${on ? "on" : "off"}`, { method: "POST" });
  showStatus(response.ok ? (on ? "Screen eingeschaltet" : "Screen ausgeschaltet") : "Fehler beim Schalten", !response.ok);
}

async function setPhotoFrame(active) {
  const status = document.getElementById("photo-frame-status");
  if (active && !await saveSettings()) return;
  try {
    const response = await fetch(`/api/photos/${active ? "show" : "hide"}`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: "{}",
    });
    const body = await response.json().catch(() => ({}));
    if (!response.ok) throw new Error(body.detail || "Reisemomente konnten nicht geschaltet werden");
    status.textContent = active ? "Reisemomente wurden gestartet." : "Reisemomente wurden beendet.";
    await updatePhotoFrameStatus();
  } catch (error) {
    status.textContent = error.message;
  }
}

async function updatePhotoFrameStatus() {
  const status = document.getElementById("photo-frame-status");
  try {
    const response = await fetch("/api/photos/status", { cache: "no-store" });
    if (!response.ok) throw new Error();
    const state = await response.json();
    if (!state.active) {
      status.textContent = "Nicht aktiv.";
      return;
    }
    const minutes = Math.floor(state.remaining_seconds / 60);
    const seconds = String(state.remaining_seconds % 60).padStart(2, "0");
    status.textContent = `Aktiv · noch ${minutes}:${seconds} Minuten`;
  } catch {
    status.textContent = "Status momentan nicht verfügbar.";
  }
}

document.getElementById("display-on-btn").addEventListener("click", () => setDisplayPower(true));
document.getElementById("arrival-test").addEventListener("click", async () => {
  const button=document.getElementById("arrival-test"),message=document.getElementById("arrival-test-status");
  const place=document.getElementById("sim-place");
  const place_name=place.value.trim();
  if (!place_name || place_name.length>120) {
    message.textContent='Bitte im Feld „Ort“ der GPS-Simulation einen Ort eingeben.';
    place.focus();return;
  }
  button.disabled=true;
  try {
    const response=await fetch("/api/arrival/test",{method:"POST",headers:{"Content-Type":"application/json"},body:JSON.stringify({place_name})});
    const body=await response.json();
    if(!response.ok)throw Error(body.detail||"Test konnte nicht gestartet werden");
    message.textContent=body.message;
    for(let i=0;i<45;i++){
      await new Promise(resolve=>setTimeout(resolve,2000));
      const status=await fetch("/api/arrival/status");
      if(!status.ok)throw Error("Teststatus nicht verfügbar");
      const data=await status.json();message.textContent=data.message;
      if(!data.loading)break;
    }
  }catch(error){message.textContent=error.message;}finally{button.disabled=false;}
});
document.getElementById("display-off-btn").addEventListener("click", () => setDisplayPower(false));
document.getElementById("photo-frame-show").addEventListener("click", () => setPhotoFrame(true));
document.getElementById("photo-frame-hide").addEventListener("click", () => setPhotoFrame(false));
document.getElementById("save-btn").addEventListener("click", saveSettings);
document.getElementById("sim-position-btn").addEventListener("click", simulatePosition);
document.getElementById("sim-disconnect-btn").addEventListener("click", stopSimulation);
document.getElementById("force-stand-btn").addEventListener("click", () => forceOperatingState("stand"));
document.getElementById("force-drive-btn").addEventListener("click", () => forceOperatingState("drive"));
document.getElementById("force-auto-btn").addEventListener("click", () => forceOperatingState("auto"));
document.getElementById("vacation-add-btn").addEventListener("click", addVacation);
loadSettings().catch(() => {
  document.getElementById('dirty-state').textContent='Einstellungen nicht geladen – bitte Seite neu laden';
  showStatus("Einstellungen konnten nicht geladen werden", true);
});
document.getElementById("calendar-refresh-btn").addEventListener("click", refreshCalendar);
updateCalendarStatus();
setInterval(updateCalendarStatus, 5000);
updatePhotoFrameStatus();
setInterval(updatePhotoFrameStatus, 1000);
