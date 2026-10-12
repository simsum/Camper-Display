const SCREEN_FACTORIES = {
  clock_flip: (settings) => createClockScreen(settings, "flip"),
  clock_blue: (settings) => createClockScreen(settings, "blue"),
  clock_blank: (settings) => createClockScreen(settings, "blank"),
  clock_panorama: createPanoramaClockScreen,
  clock_led: createLedClockScreen,
  clock_linear: createLinearClockScreen,
  clock_marble: createMarbleClockScreen,
  journey: createJourneyScreen,
  map: createMapScreen,
  weather: createWeatherScreen,
  sun: createSunScreen,
  calendar: createCalendarScreen,
};

const SETTINGS_POLL_MS = 5000;

class App {
  constructor() {
    this.stageEl = document.getElementById("stage");
    this.screensEl = document.getElementById("screens");
    this.dimmerEl = document.getElementById("display-dimmer");
    this.qrTriggerEl = document.getElementById("photo-qr-trigger");
    this.qrScreenEl = document.getElementById("photo-qr-screen");
    this.screens = [];
    this.currentIndex = 0;
    this.mode = "stand";
    this.settings = null;
    this.lastSettingsJson = null;
    this.status = null;
    this.rotationTimer = null;
    this.displaySuspended = "";
    this.nightScreen = null;
    this.arrivalScreen = null;
    this.photoFrameScreen = null;
    this.qrVisibleUntil = 0;
    this.arrivalId = null;
    this.dismissedArrivalId = null;
    this.lastAvailableCount = 0;
  }

  async init() {
    this.settings = await this.fetchSettings();
    this.lastSettingsJson = JSON.stringify(this.settings);
    this.applyStageSize();
    window.addEventListener("resize", () => this.applyStageSize());
    this.buildScreens();
    this.attachTouch();
    ["pointerdown", "touchstart", "touchend"].forEach(type => this.qrTriggerEl?.addEventListener(type, event => event.stopPropagation()));
    this.qrTriggerEl?.addEventListener("click", event => { event.stopPropagation(); this.showPhotoQr(); });
    this.qrScreenEl?.addEventListener("click", () => { this.qrVisibleUntil = 0; this.updateDisplayState(); });
    this.loadPhotoShare();
    this.startPolling();
    // Local time must keep running even if the backend or network is unavailable.
    setInterval(() => {
      if (this.displaySuspended === "arrival") this.updateDisplayState();
      if (this.displaySuspended === "photo") {
        this.safeCall(this.photoFrameScreen, "onTick", this.status, this.settings);
        this.updateDisplayState();
        return;
      }
      if (this.displaySuspended === "qr") {
        this.updateDisplayState();
        return;
      }
      if (this.displaySuspended === "night") {
        this.safeCall(this.nightScreen, "onTick", this.status, this.settings);
        return;
      }
      if (this.displaySuspended) return;
      const screen = this.screens[this.currentIndex];
      if (screen?.isClock) this.safeCall(screen, "onTick", this.status, this.settings);
    }, 1000);
    this.startSettingsSync();
    this.resetRotation();
  }

  applyStageSize() {
    const width = this.settings.display_width || 1480;
    const height = this.settings.display_height || 320;
    this.stageEl.style.setProperty("--stage-width", `${width}px`);
    this.stageEl.style.setProperty("--stage-height", `${height}px`);
    const nativeSize = Math.abs(window.innerWidth - width) <= 4
      && Math.abs(window.innerHeight - height) <= 4;
    const scale = Math.min(window.innerWidth / width, window.innerHeight / height);
    this.stageEl.style.transform = nativeSize ? "none" : `scale(${scale})`;
    const panelOpacity = Math.max(10, Math.min(95, this.settings.panel_opacity_percent ?? 52));
    this.stageEl.style.setProperty("--panel-opacity", String(panelOpacity / 100));
    const panelBlur = Math.max(0, Math.min(16, this.settings.panel_blur_pixels ?? 0));
    this.stageEl.style.setProperty("--panel-blur", `${panelBlur}px`);
    this.applyThemeBackground();
  }

  async loadPhotoShare() {
    const address = document.getElementById("photo-upload-address");
    const image = document.getElementById("photo-upload-qr");
    if (!address || !image) return;
    try {
      const response = await fetch("/api/photos/share", {cache:"no-store"});
      if (!response.ok) throw new Error("Photo share unavailable");
      const {url} = await response.json();
      address.textContent = url || "LAN-Adresse des Displays noch nicht eingerichtet";
      if (url) {
        image.src = "/api/photos/qr.svg";
        image.parentElement.hidden = false;
      }
    } catch (_) {
      address.textContent = "Fotoseite: Display-Adresse mit /photos im Handy-Browser öffnen";
    }
  }

  applyThemeBackground() {
    if (this.displaySuspended) { document.body.style.background = "#000"; return; }
    const colors = this.settings.theme_background_colors || {};
    const themeId = this.screens[this.currentIndex]?.themeId || this.settings.theme;
    document.body.style.background = colors[themeId] || "#000000";
  }

  applyBrightness() {
    const value = this.status?.display?.brightness_percent
      ?? (this.mode === "drive" ? this.settings.brightness_drive : this.settings.brightness_stand)
      ?? 100;
    const brightness = this.status?.display?.brightness_control === "hardware"
      ? 100 : Math.max(1, Math.min(100, value));
    this.stageEl.style.filter = "none";
    if (this.dimmerEl) {
      this.dimmerEl.style.opacity = String(1 - brightness / 100);
    }
  }

  async fetchSettings() {
    const resp = await fetch("/api/settings");
    if (!resp.ok) throw new Error("Einstellungen nicht verfügbar");
    return resp.json();
  }

  updateDisplayState() {
    const display = this.status?.display;
    let next = display?.display_on === false ? "off" : display?.night_clock_active ? "night" : "";
    const arrival = this.status?.arrival;
    const arrivalAllowed = arrival?.event_id && arrival.expires_at * 1000 > Date.now()
      && arrival.event_id !== this.dismissedArrivalId && !arrival.suppressed
      && (this.settings.arrival_enabled !== false || arrival.data?.test)
      && this.status?.operating?.mode !== "drive";
    if (next || arrival?.suppressed) this.dismissedArrivalId = arrival?.event_id || this.dismissedArrivalId;
    if (!next && arrivalAllowed) next = "arrival";
    const photoAllowed = this.status?.photo_frame?.active === true
      && this.status?.operating?.mode !== "drive";
    if (!next && photoAllowed) next = "photo";
    const qrAllowed = this.qrVisibleUntil > Date.now()
      && this.status?.operating?.mode !== "drive";
    if (!next && qrAllowed) next = "qr";
    if (next === "arrival" && this.arrivalId !== arrival.event_id) {
      this.arrivalScreen?.element.remove();
      this.arrivalScreen = createArrivalScreen(arrival.data);
      this.arrivalId = arrival.event_id;
      this.stageEl.appendChild(this.arrivalScreen.element);
      this.arrivalScreen.element.classList.toggle("screen-active", true);
    }
    if (next === this.displaySuspended) { this.updateQrTrigger(); return; }
    const active = this.screens[this.currentIndex];
    if (active && !this.displaySuspended) this.safeCall(active, "onUnmount");
    clearTimeout(this.rotationTimer);
    this.displaySuspended = next;
    if (this.arrivalScreen) {
      this.arrivalScreen.element.classList.toggle("screen-active", next === "arrival");
      this.arrivalScreen.element.setAttribute("aria-hidden", next === "arrival" ? "false" : "true");
    }
    if (next === "photo" && !this.photoFrameScreen) {
      this.photoFrameScreen = createPhotoFrameScreen();
      this.stageEl.appendChild(this.photoFrameScreen.element);
    }
    if (this.photoFrameScreen) {
      const photoActive = next === "photo";
      this.photoFrameScreen.element.classList.toggle("screen-active", photoActive);
      this.photoFrameScreen.element.setAttribute("aria-hidden", photoActive ? "false" : "true");
      if (photoActive) this.safeCall(this.photoFrameScreen, "onMount");
      else this.safeCall(this.photoFrameScreen, "onUnmount");
    }
    if (this.qrScreenEl) {
      const qrActive = next === "qr";
      this.qrScreenEl.classList.toggle("screen-active", qrActive);
      this.qrScreenEl.setAttribute("aria-hidden", qrActive ? "false" : "true");
    }
    if (next === "night" && !this.nightScreen) {
      this.nightScreen = createNightClockScreen(this.settings);
      this.stageEl.appendChild(this.nightScreen.element);
    }
    if (this.nightScreen) {
      this.nightScreen.element.classList.toggle("screen-active", next === "night");
      this.nightScreen.element.setAttribute("aria-hidden", next === "night" ? "false" : "true");
      if (next === "night") this.safeCall(this.nightScreen, "onTick", this.status, this.settings);
    }
    this.renderCurrentScreen();
    if (!next) {
      if (active) this.safeCall(active, "onMount");
      this.resetRotation();
    }
    this.updateQrTrigger();
  }

  showPhotoQr() {
    if (!this.qrTriggerEl?.classList.contains("enabled")) return;
    this.qrVisibleUntil = Date.now() + 90000;
    this.updateDisplayState();
  }

  updateQrTrigger() {
    const mode = this.status?.operating?.mode || this.mode;
    const enabled = !this.displaySuspended && mode !== "drive"
      && this.screens[this.currentIndex]?.isClock === true;
    this.qrTriggerEl?.classList.toggle("enabled", enabled);
  }

  modeConfig(config) {
    if (this.mode === "drive") {
      return { enabled: config.drive_enabled, durationSeconds: config.drive_duration_seconds };
    }
    return { enabled: config.stand_enabled, durationSeconds: config.stand_duration_seconds };
  }

  buildScreens() {
    clearTimeout(this.rotationTimer);
    this.screens.forEach(screen => this.safeCall(screen, "onUnmount"));
    this.screens.forEach(screen => this.safeCall(screen, "onDispose"));
    this.screensEl.innerHTML = "";
    this.screens = this.settings.screens
      .filter((config) => this.modeConfig(config).enabled && SCREEN_FACTORIES[config.id])
      .map((config) => {
        let screen;
        try {
          screen = SCREEN_FACTORIES[config.id](this.settings);
        } catch (error) {
          console.error(`Screen ${config.id} konnte nicht geladen werden`, error);
          screen = createModuleFallbackScreen(config.id);
        }
        screen.config = config;
        screen.moduleId = config.id;
        return screen;
      });

    this.screens.forEach((screen) => {
      this.screensEl.appendChild(screen.element);
    });

    this.currentIndex = this.firstAvailableIndex();
    this.renderCurrentScreen();
    if (this.screens[this.currentIndex] && !this.displaySuspended) {
      this.safeCall(this.screens[this.currentIndex], "onMount");
    }
    this.tickScreens();
    this.resetRotation();
  }

  safeCall(screen, method, ...args) {
    try {
      screen[method]?.(...args);
    } catch (error) {
      console.error(`Screen ${screen.moduleId || "unknown"}: ${method}`, error);
    }
  }

  isAvailable(screen) {
    try {
      return screen.isAvailable?.(this.status, this.settings) !== false;
    } catch (error) {
      console.error(`Verfügbarkeit von ${screen.moduleId} konnte nicht ermittelt werden`, error);
      return false;
    }
  }

  availableIndexes() {
    return this.screens
      .map((screen, index) => (this.isAvailable(screen) ? index : -1))
      .filter((index) => index >= 0);
  }

  firstAvailableIndex() {
    return this.availableIndexes()[0] ?? 0;
  }

  findNextAvailable(step) {
    if (this.screens.length === 0) return null;
    for (let offset = 1; offset <= this.screens.length; offset += 1) {
      const index = (this.currentIndex + step * offset + this.screens.length) % this.screens.length;
      if (this.isAvailable(this.screens[index])) return index;
    }
    return this.isAvailable(this.screens[this.currentIndex]) ? this.currentIndex : null;
  }

  renderCurrentScreen() {
    this.applyThemeBackground();
    if (this.screens.length === 0) {
      document.body.dataset.activeModule = "";
      this.updateQrTrigger();
      return;
    }
    document.body.dataset.activeModule = this.displaySuspended || this.screens[this.currentIndex]?.moduleId || "";
    this.applyThemeBackground();
    this.screens.forEach((screen, index) => {
      const active = index === this.currentIndex && !this.displaySuspended;
      screen.element.classList.toggle("screen-active", active);
      screen.element.setAttribute("aria-hidden", active ? "false" : "true");
    });
    this.updateQrTrigger();
  }

  goTo(index) {
    if (this.displaySuspended) return;
    if (index == null || this.screens.length === 0) return;
    this.safeCall(this.screens[this.currentIndex], "onUnmount");
    this.currentIndex = index;
    this.renderCurrentScreen();
    this.safeCall(this.screens[this.currentIndex], "onMount");
    if (this.status) {
      this.safeCall(this.screens[this.currentIndex], "onTick", this.status, this.settings);
    }
    this.resetRotation();
  }

  goBy(step) {
    this.goTo(this.findNextAvailable(step));
  }

  attachTouch() {
    let startX = null;
    let startedWhileOff = false;
    let arrivalTouchConsumed = false;
    document.body.addEventListener("pointerdown", () => {
      arrivalTouchConsumed = this.displaySuspended === "arrival";
      if (this.displaySuspended === "arrival") {
        this.dismissedArrivalId = this.arrivalId;
        this.updateDisplayState();
        return;
      }
      if (this.displaySuspended || this.status?.operating?.manual_wake_active) {
        fetch("/api/display/wake", {method:"POST"}).catch(error => console.error("Aufwecken fehlgeschlagen", error));
      }
    });

    document.body.addEventListener("touchstart", (event) => {
      startX = event.touches[0].clientX;
      startedWhileOff = Boolean(this.displaySuspended) || arrivalTouchConsumed;
    });

    document.body.addEventListener("touchend", (event) => {
      if (startX === null) return;
      const deltaX = event.changedTouches[0].clientX - startX;
      startX = null;
      arrivalTouchConsumed = false;
      if (startedWhileOff) return;
      if (deltaX > 50) this.goBy(-1);
      else this.goBy(1);
    });
  }

  resetRotation() {
    clearTimeout(this.rotationTimer);
    if (this.displaySuspended) return;
    const available = this.availableIndexes();
    this.lastAvailableCount = available.length;
    if (available.length <= 1 || !this.screens[this.currentIndex]) return;
    const duration = this.modeConfig(this.screens[this.currentIndex].config).durationSeconds || 30;
    this.rotationTimer = setTimeout(() => this.goBy(1), duration * 1000);
  }

  tickScreens() {
    if (this.displaySuspended) return;
    if (!this.status) return;
    if (this.availableIndexes().length !== this.lastAvailableCount) this.resetRotation();
    if (this.screens[this.currentIndex] && !this.isAvailable(this.screens[this.currentIndex])) {
      this.goBy(1);
    } else {
      if (this.screens[this.currentIndex]) {
        this.safeCall(this.screens[this.currentIndex], "onTick", this.status, this.settings);
      }
      this.renderCurrentScreen();
    }
  }

  startPolling() {
    const poll = async () => {
      try {
        const resp = await fetch("/api/status");
        if (!resp.ok) throw new Error("Status nicht verfügbar");
        this.status = await resp.json();
      } catch (error) {
        console.error(error);
        return;
      }

      const freshMode = this.status.operating?.mode || "stand";
      this.updateDisplayState();
      this.applyBrightness();
      if (freshMode !== this.mode) {
        this.mode = freshMode;
        this.buildScreens();
        return;
      }
      this.tickScreens();
    };
    poll();
    setInterval(poll, 1000);
  }

  startSettingsSync() {
    const sync = async () => {
      let fresh;
      try {
        fresh = await this.fetchSettings();
      } catch (error) {
        return;
      }
      const freshJson = JSON.stringify(fresh);
      if (freshJson === this.lastSettingsJson) return;

      this.lastSettingsJson = freshJson;
      this.settings = fresh;
      if (this.nightScreen) {
        this.nightScreen.element.remove();
        this.nightScreen = null;
        // Recreate with fresh dimensions, font settings and color.
        if (this.displaySuspended === "night") {
          this.nightScreen = createNightClockScreen(this.settings);
          this.stageEl.appendChild(this.nightScreen.element);
          this.nightScreen.element.classList.toggle("screen-active", true);
          this.safeCall(this.nightScreen, "onTick", this.status, this.settings);
        }
      }
      this.applyStageSize();
      this.applyBrightness();
      this.buildScreens();
    };
    setInterval(sync, SETTINGS_POLL_MS);
  }
}

function createModuleFallbackScreen(moduleId) {
  const element = document.createElement("div");
  element.className = "screen module-placeholder";
  element.innerHTML = `
    <div class="module-placeholder-icon">⚠</div>
    <div class="module-placeholder-title">Modul nicht verfügbar</div>
    <div class="module-placeholder-copy">${moduleId}</div>
  `;
  return { element, onMount() {}, onTick() {}, isAvailable() { return false; } };
}

window.addEventListener("DOMContentLoaded", () => {
  const app = new App();
  app.init();
});
