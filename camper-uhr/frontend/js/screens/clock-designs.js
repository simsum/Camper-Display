// Pure time calculations are shared by the three offline-capable clock modules.
function clockDisplayParts(now, settings = {}) {
  const hour24 = now.getHours();
  const twelve = settings.time_format_24h === false;
  const hour = twelve ? hour24 % 12 || 12 : hour24;
  return {
    hour, hour24, minute: now.getMinutes(), second: now.getSeconds(), twelve,
    hh: String(hour).padStart(2, "0"), mm: String(now.getMinutes()).padStart(2, "0"),
    ss: String(now.getSeconds()).padStart(2, "0"),
    ampm: twelve ? (hour24 < 12 ? "AM" : "PM") : "",
    progress: (hour24 * 3600 + now.getMinutes() * 60 + now.getSeconds()) / 86400,
    period: hour24 < 5 ? "Nacht" : hour24 < 10 ? "Morgen" : hour24 < 18 ? "Tag" : hour24 < 22 ? "Abend" : "Nacht",
    dateKey: `${now.getFullYear()}-${now.getMonth()}-${now.getDate()}`,
  };
}

function clockRulerValues(value, modulus, start = 0, radius = 4) {
  return Array.from({ length: radius * 2 + 1 }, (_, index) => (value - start + index - radius + modulus) % modulus + start);
}

function clockRulerShouldSlide(previous, next, modulus, elapsed) {
  return previous !== null && elapsed > 0 && elapsed <= 2000
    && (next - previous + modulus) % modulus === 1;
}

function clockLedShouldRefresh(previousTime, nextTime) {
  return previousTime !== null && nextTime > previousTime && nextTime - previousTime <= 2000
    && Math.floor(nextTime / 60000) === Math.floor(previousTime / 60000) + 1;
}

function clockLedRefreshFrames(target, random = Math.random) {
  const count = 8 + Math.floor(random() * 4);
  const duration = 1200 + Math.floor(random() * 450);
  let previous = Number(target);
  const frames = Array.from({ length: count }, (_, index) => {
    previous = (previous + 1 + Math.floor(random() * 9)) % 10;
    return { at: Math.round(duration * (index / count) ** 1.3), value: String(previous) };
  });
  frames.push({ at: duration, value: String(target) });
  return frames;
}

// Solar times use the same local ISO values as the Himmel module. Explicit
// offsets are converted to the clock's timezone; yesterday's data are rejected.
function clockSolarBand(status, now) {
  const missing = { available: false, background: "linear-gradient(90deg,#26344f,#58647d 50%,#26344f)", period: "—", times: "Keine aktuellen Sonnendaten" };
  const weather = status?.weather;
  if (!weather?.available) return missing;
  if (status.server_time_iso) {
    const age = now.getTime() - Date.parse(status.server_time_iso);
    if (!Number.isFinite(age) || age > 7200000 || age < -300000) return missing;
  }
  const sameDay = date => date.getFullYear() === now.getFullYear() && date.getMonth() === now.getMonth() && date.getDate() === now.getDate();
  function event(value) {
    if (typeof value !== "string" || !/^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}/.test(value)) return null;
    const date = new Date(value);
    if (!Number.isFinite(date.getTime()) || !sameDay(date)) return null;
    return { minutes: date.getHours() * 60 + date.getMinutes() + date.getSeconds() / 60,
      text: date.toLocaleTimeString("de-DE", { hour: "2-digit", minute: "2-digit", hour12: false }) };
  }
  const rise = event(weather.sunrise), set = event(weather.sunset);
  if (!rise || !set || set.minutes <= rise.minutes) return missing;
  // These short blends are decorative, not a claim to calculated twilight.
  const blend = Math.min(45, (set.minutes - rise.minutes) / 4);
  const percent = minute => (Math.max(0, Math.min(1440, minute)) / 1440 * 100).toFixed(4) + "%";
  const stops = [
    ["#1b2954", 0], ["#1b2954", rise.minutes - blend],
    ["#ba786c", rise.minutes], ["#e9bf83", rise.minutes + blend],
    ["#f2d899", (rise.minutes + set.minutes) / 2],
    ["#d6aa78", set.minutes - blend], ["#bc736b", set.minutes],
    ["#1b2954", set.minutes + blend], ["#1b2954", 1440],
  ];
  const minutes = now.getHours() * 60 + now.getMinutes() + now.getSeconds() / 60;
  return { available: true, sunrise: rise.minutes, sunset: set.minutes,
    background: `linear-gradient(90deg,${stops.map(([color, minute]) => `${color} ${percent(minute)}`).join(",")})`,
    period: minutes >= rise.minutes && minutes < set.minutes ? "Tag" : "Nacht",
    times: `↑ ${rise.text} · ↓ ${set.text}` };
}

const CLOCK_LED_GLYPHS = [
  "01110100011001110101110011000101110", "00100011000010000100001000010001110",
  "01110100010000100010001000100011111", "11110000010000101110000010000111110",
  "00010001100101010010111110001000010", "11111100001000011110000010000111110",
  "01110100001000011110100011000101110", "11111000010001000100010000100001000",
  "01110100011000101110100011000101110", "01110100011000101111000010000101110",
];

function createModernClockScreen(settings, kind) {
  const element = document.createElement("div");
  element.className = `screen clock-display clock-${kind}`;
  element.setAttribute("role", "img");
  const ampm = '<span class="clock-ampm" data-clock="ampm"></span>';
  if (kind === "panorama") {
    element.innerHTML = `
      <div class="clock-ridge"></div><div class="clock-ridge near"></div>
      <div class="clock-date"><div class="clock-eyebrow" data-clock="weekday"></div><strong data-clock="date"></strong><small data-clock="year"></small></div>
      <div class="clock-time"><span data-clock="hm"></span><span class="clock-seconds" data-clock="ss"></span>${ampm}</div>
      <div class="clock-daypart"><div class="clock-eyebrow">TAGESLAUF</div><strong data-clock="period"></strong><div class="clock-sun-times" data-clock="sun-times"></div></div>
      <div class="clock-dayband"><div class="clock-daymarker"></div></div>
      <div class="clock-daylabels"><span>00</span><span>06</span><span>12</span><span>18</span><span>24</span></div>`;
  } else if (kind === "led") {
    element.innerHTML = `
      <div class="clock-led-side"><div class="clock-eyebrow">WOCHENTAG</div><strong data-clock="weekday"></strong></div>
      <div class="clock-matrix" aria-hidden="true"></div>${ampm}
      <div class="clock-led-side right"><div class="clock-eyebrow">DATUM</div><strong data-clock="shortdate"></strong><small data-clock="year"></small></div>`;
  } else {
    element.innerHTML = `
      <div class="clock-linear-header"><div class="clock-eyebrow">ZEIT · IM FOKUS ${ampm}</div><div class="clock-eyebrow" data-clock="fulldate"></div></div>
      <div class="clock-rulers">${["STUNDEN", "MINUTEN", "SEKUNDEN"].map((label) => `<div class="clock-ruler"><span class="clock-ruler-name">${label}</span><div class="clock-scale"></div></div>`).join("")}</div>`;
  }

  const textNodes = new Map(Array.from(element.querySelectorAll("[data-clock]"), node => [node.dataset.clock, node]));
  function setText(key, value) {
    const node = textNodes.get(key);
    if (node && node.textContent !== value) node.textContent = value;
  }
  const matrix = element.querySelector(".clock-matrix");
  const ledDigits = [];
  if (matrix) {
    for (let index = 0; index < 4; index++) {
      if (index === 2) {
        const colon = document.createElement("span");
        colon.className = "clock-matrix-colon";
        matrix.appendChild(colon);
      }
      const digit = document.createElement("div");
      digit.className = "clock-matrix-digit";
      const dots = Array.from({ length: 35 }, () => {
        const dot = document.createElement("span"); digit.appendChild(dot); return dot;
      });
      matrix.appendChild(digit);
      ledDigits.push({ element: digit, dots, last: null, shown: null });
    }
  }
  const rulers = Array.from(element.querySelectorAll(".clock-scale"), scale => {
    const track = document.createElement("div");
    track.className = "clock-ruler-track";
    scale.appendChild(track);
    const ticks = Array.from({ length: 11 }, (_, index) => {
      const tick = document.createElement("span");
      tick.className = "clock-tick" + (index === 5 ? " active" : "");
      track.appendChild(tick); return tick;
    });
    return { track, ticks, value: null, modulus: null, animation: null };
  });
  const marker = element.querySelector(".clock-daymarker");
  const dayband = element.querySelector(".clock-dayband");
  let lastStatus = null;
  let lastBandBackground = null;
  let lastDate = null;
  let lastNow = null;
  let lastLedFormat = null;
  let ledTimer = null;
  function paintLed(digit, value) {
    if (value === null || digit.shown === value) return;
    const glyph = CLOCK_LED_GLYPHS[Number(value)];
    digit.dots.forEach((dot, bit) => dot.classList.toggle("on", glyph[bit] === "1"));
    digit.shown = value;
  }
  function cancelLedRefresh() {
    if (ledTimer !== null) clearTimeout(ledTimer);
    ledTimer = null;
    if (matrix) matrix.dataset.refreshing = "false";
    ledDigits.forEach(digit => paintLed(digit, digit.last));
  }
  function startLedRefresh() {
    const plans = ledDigits.map(digit => clockLedRefreshFrames(digit.last));
    const started = performance.now();
    matrix.dataset.refreshing = "true";
    matrix.dataset.refreshRun = String(Number(matrix.dataset.refreshRun || 0) + 1);
    const advance = () => {
      if (!element.isConnected || !element.classList.contains("screen-active")
          || document.visibilityState === "hidden"
          || globalThis.matchMedia?.("(prefers-reduced-motion: reduce)").matches) {
        cancelLedRefresh(); return;
      }
      const elapsed = performance.now() - started;
      let finished = true;
      plans.forEach((frames, index) => {
        let frame = frames[0];
        for (const candidate of frames) { if (candidate.at > elapsed) break; frame = candidate; }
        paintLed(ledDigits[index], frame.value);
        if (elapsed < frames[frames.length - 1].at) finished = false;
      });
      if (finished) cancelLedRefresh();
      else ledTimer = setTimeout(advance, 50);
    };
    advance();
  }
  function update(currentSettings = settings, now = new Date(), allowMotion = true) {
    const parts = clockDisplayParts(now, currentSettings);
    setText("hm", `${parts.hh}:${parts.mm}`);
    setText("ss", parts.ss);
    setText("ampm", parts.ampm);
    setText("period", parts.period);
    if (marker) {
      marker.style.left = `${parts.progress * 100}%`;
      const solar = clockSolarBand(lastStatus, now);
      setText("period", solar.period);
      setText("sun-times", solar.times);
      if (lastBandBackground !== solar.background) {
        dayband.style.background = solar.background;
        dayband.dataset.solarAvailable = String(solar.available);
        lastBandBackground = solar.background;
      }
    }
    const digits = parts.hh + parts.mm + parts.ss;
    const ledChanged = ledDigits.some((digit, index) => digit.last !== digits[index]);
    const refresh = matrix && ledChanged && allowMotion && lastLedFormat === parts.twelve
      && clockLedShouldRefresh(lastNow, now.getTime())
      && element.isConnected && element.classList.contains("screen-active")
      && document.visibilityState !== "hidden"
      && !globalThis.matchMedia?.("(prefers-reduced-motion: reduce)").matches;
    if (ledChanged) cancelLedRefresh();
    ledDigits.forEach((digit, index) => {
      if (digit.last === digits[index]) return;
      digit.last = digits[index];
      paintLed(digit, digit.last);
    });
    if (refresh) {
      // Whole digits shuffle independently, slow down, and settle on HH:MM.
      // The colon and background stay lit; one bounded timer serves the board.
      startLedRefresh();
    }
    lastLedFormat = parts.twelve;
    rulers.forEach((ruler, index) => {
      const next = [parts.hour, parts.minute, parts.second][index];
      const modulus = index === 0 ? (parts.twelve ? 12 : 24) : 60;
      if (ruler.value === next && ruler.modulus === modulus) return;
      const slide = allowMotion && ruler.modulus === modulus
        && clockRulerShouldSlide(ruler.value, next, modulus, now.getTime() - lastNow)
        && element.isConnected && element.classList.contains("screen-active")
        && document.visibilityState !== "hidden"
        && !globalThis.matchMedia?.("(prefers-reduced-motion: reduce)").matches;
      ruler.animation?.cancel();
      ruler.animation = null;
      const values = clockRulerValues(next, modulus, index === 0 && parts.twelve ? 1 : 0, 5);
      ruler.ticks.forEach((tick, i) => {
        const value = String(values[i]).padStart(2, "0");
        if (tick.textContent !== value) tick.textContent = value;
      });
      // One spare cell at each edge keeps wraps filled. The new strip starts
      // one cell right of its resting position, then slides left under the marker.
      if (slide && typeof ruler.track.animate === "function") {
        const animation = ruler.track.animate([
          { transform: `translateX(${100 / 11}%)` }, { transform: "translateX(0)" },
        ], { duration: 250, easing: "cubic-bezier(.22,.61,.36,1)" });
        ruler.animation = animation;
        animation.onfinish = () => { if (ruler.animation === animation) ruler.animation = null; };
      }
      ruler.value = next;
      ruler.modulus = modulus;
    });
    lastNow = now.getTime();
    if (lastDate !== parts.dateKey) {
      setText("weekday", now.toLocaleDateString("de-DE", { weekday: "long" }));
      setText("date", now.toLocaleDateString("de-DE", { day: "numeric", month: "long" }));
      setText("shortdate", now.toLocaleDateString("de-DE", { day: "2-digit", month: "2-digit" }));
      setText("month", now.toLocaleDateString("de-DE", { month: "long" }));
      setText("year", String(now.getFullYear()));
      setText("fulldate", now.toLocaleDateString("de-DE", { weekday: "long", day: "numeric", month: "long", year: "numeric" }));
      lastDate = parts.dateKey;
    }
    element.setAttribute("aria-label", `${parts.hh}:${parts.mm}${kind === "led" ? "" : ":" + parts.ss} ${parts.ampm}`.trim());
  }
  update(settings);
  return { element, isClock: true, onMount() {
    cancelLedRefresh();
    rulers.forEach(ruler => { ruler.animation?.cancel(); ruler.animation = null; });
    update(settings, new Date(), false);
  }, onUnmount() {
    cancelLedRefresh();
    rulers.forEach(ruler => { ruler.animation?.cancel(); ruler.animation = null; });
  }, onTick(status, currentSettings, now) { lastStatus = status; update(currentSettings, now); } };
}

function createPanoramaClockScreen(settings) { return createModernClockScreen(settings, "panorama"); }
function createLedClockScreen(settings) { return createModernClockScreen(settings, "led"); }
function createLinearClockScreen(settings) { return createModernClockScreen(settings, "linear"); }
