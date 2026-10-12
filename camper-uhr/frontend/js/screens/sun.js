function createSunScreen() {
  const el = document.createElement("div");
  el.className = "screen sky-screen";
  el.innerHTML = `
    <div class="sky-scene">
      <section class="sky-side sky-glass sky-sun-panel">
        <div class="sky-identity">
          <div class="sky-sun-orb"></div>
          <div class="sky-identity-copy">
            <div class="sky-eyebrow">SONNE</div>
            <div class="sky-name" id="sky-sun-status">–</div>
            <div class="sky-status" id="sky-sun-remaining">–</div>
          </div>
        </div>
        <div class="sky-metric-row">
          <div class="sky-metric"><div class="sky-metric-label">AUFGANG</div><div class="sky-metric-value" id="sky-sunrise">--:--</div><div class="sky-metric-sub">Osten</div></div>
          <div class="sky-metric"><div class="sky-metric-label">UNTERGANG</div><div class="sky-metric-value" id="sky-sunset">--:--</div><div class="sky-metric-sub">Westen</div></div>
        </div>
      </section>

      <section class="sky-center sky-glass">
        <div class="sky-center-top"><div class="sky-center-title">HIMMEL HEUTE</div><div class="sky-date" id="sky-date">–</div></div>
        <div class="sky-arc">
          <svg viewBox="0 0 620 150" preserveAspectRatio="none" aria-hidden="true">
            <defs><linearGradient id="sky-day-arc" x1="0" x2="1"><stop offset="0" stop-color="#ffb24d"/><stop offset=".60" stop-color="#ffe397"/><stop offset="1" stop-color="#80cfff"/></linearGradient></defs>
            <path d="M8 142 Q310 -62 612 142" class="sky-arc-shadow"/><path d="M8 142 Q310 -62 612 142" class="sky-arc-line"/>
            <circle cx="8" cy="142" r="5" fill="#ffb24d"/><circle cx="612" cy="142" r="5" fill="#8dd9ff"/>
            <circle id="sky-now-dot" class="sky-now-dot" cx="8" cy="142" r="15"/>
          </svg>
        </div>
        <div class="sky-now-label" id="sky-now-label">--:-- · JETZT</div>
        <div class="sky-horizon"></div>
        <div class="sky-summary">
          <div class="sky-summary-item"><div class="sky-summary-label">TAGESLÄNGE</div><div class="sky-summary-value sky-gold" id="sky-day-length">–</div></div>
          <div class="sky-summary-item"><div class="sky-summary-label" id="sky-next-sun-label">SONNE BIS</div><div class="sky-summary-value" id="sky-next-sun">--:--</div></div>
        </div>
      </section>

      <section class="sky-side sky-glass sky-moon-panel">
        <div class="sky-identity">
          <div class="sky-moon-orb" id="sky-moon-orb"><div class="sky-moon-shadow"></div></div>
          <div class="sky-identity-copy">
            <div class="sky-eyebrow" id="sky-moon-name">MOND</div>
            <div class="sky-name" id="sky-moon-light">-- % beleuchtet</div>
            <div class="sky-status sky-visibility" id="sky-moon-status">–</div>
          </div>
        </div>
        <div class="sky-metric-row">
          <div class="sky-metric"><div class="sky-metric-label">AUFGANG</div><div class="sky-metric-value" id="sky-moonrise">--:--</div><div class="sky-metric-sub">Mondaufgang</div></div>
          <div class="sky-metric"><div class="sky-metric-label">UNTERGANG</div><div class="sky-metric-value" id="sky-moonset">--:--</div><div class="sky-metric-sub">Monduntergang</div></div>
        </div>
      </section>
    </div>
  `;

  function timeParts(iso) {
    const match = typeof iso === "string" && iso.match(/T(\d{2}):(\d{2})/);
    return match ? { text: `${match[1]}:${match[2]}`, minutes: Number(match[1]) * 60 + Number(match[2]) } : null;
  }

  function formatDuration(totalMinutes) {
    const minutes = Math.max(0, Math.round(totalMinutes));
    const hours = Math.floor(minutes / 60);
    const rest = minutes % 60;
    if (hours === 0) return `${rest} Min.`;
    return `${hours} Std. ${String(rest).padStart(2, "0")} Min.`;
  }

  function intervalContains(now, start, end) {
    if (start == null || end == null) return false;
    return start <= end ? now >= start && now < end : now >= start || now < end;
  }

  function minutesUntil(now, target) {
    return (target - now + 1440) % 1440;
  }

  function setText(selector, value) {
    el.querySelector(selector).textContent = value;
  }

  function updateArc(nowMinutes, sunriseMinutes, sunsetMinutes, nowText) {
    const dot = el.querySelector("#sky-now-dot");
    const label = el.querySelector("#sky-now-label");
    const daytime = intervalContains(nowMinutes, sunriseMinutes, sunsetMinutes) && sunriseMinutes < sunsetMinutes;
    let fraction = 0;
    if (sunriseMinutes != null && sunsetMinutes != null && sunsetMinutes > sunriseMinutes) {
      fraction = Math.max(0, Math.min(1, (nowMinutes - sunriseMinutes) / (sunsetMinutes - sunriseMinutes)));
    }
    const x = 8 + fraction * 604;
    const y = 142 - 204 * 4 * fraction * (1 - fraction);
    dot.setAttribute("cx", x.toFixed(1));
    dot.setAttribute("cy", y.toFixed(1));
    dot.classList.toggle("sky-now-dot-night", !daytime);
    label.style.left = `${Math.max(12, Math.min(88, 4.2 + fraction * 91.6))}%`;
    label.style.top = `${Math.max(52, Math.min(154, 48 + y * 0.72))}px`;
    label.textContent = `${nowText} · JETZT`;
  }

  function updateMoonShape(fraction) {
    const orb = el.querySelector("#sky-moon-orb");
    const phaseIndex = Math.round(((Number(fraction) || 0) % 1) * 8) % 8;
    orb.className = `sky-moon-orb sky-moon-phase-${phaseIndex}`;
  }

  return {
    element: el,
    onMount() {},
    isAvailable(status) {
      return Boolean(status?.weather?.available && status.weather.sunrise && status.weather.sunset && status.moon?.moonrise && status.moon?.moonset);
    },
    onTick(status) {
      const weather = status.weather || {};
      const moon = status.moon || {};
      const now = new Date(status.server_time_iso || Date.now());
      const nowMinutes = now.getHours() * 60 + now.getMinutes();
      const nowText = now.toLocaleTimeString("de-DE", { hour: "2-digit", minute: "2-digit" });
      const sunrise = timeParts(weather.sunrise);
      const sunset = timeParts(weather.sunset);
      const moonrise = timeParts(moon.moonrise);
      const moonset = timeParts(moon.moonset);
      const sunUp = intervalContains(nowMinutes, sunrise?.minutes, sunset?.minutes);
      const moonUp = intervalContains(nowMinutes, moonrise?.minutes, moonset?.minutes);

      setText("#sky-date", now.toLocaleDateString("de-DE", { weekday: "long", day: "2-digit", month: "long" }));
      setText("#sky-sunrise", sunrise?.text || "--:--");
      setText("#sky-sunset", sunset?.text || "--:--");
      setText("#sky-sun-status", sunUp ? "Über dem Horizont" : "Unter dem Horizont");
      setText("#sky-sun-remaining", sunUp ? `Noch ${formatDuration(minutesUntil(nowMinutes, sunset.minutes))} Tageslicht` : `Aufgang in ${formatDuration(minutesUntil(nowMinutes, sunrise.minutes))}`);

      const daylightMinutes = Number(weather.daylight_duration_seconds) / 60;
      setText("#sky-day-length", Number.isFinite(daylightMinutes) ? formatDuration(daylightMinutes) : "–");
      setText("#sky-next-sun-label", sunUp ? "SONNE BIS" : "SONNE AB");
      setText("#sky-next-sun", sunUp ? sunset?.text || "--:--" : sunrise?.text || "--:--");
      updateArc(nowMinutes, sunrise?.minutes, sunset?.minutes, nowText);

      const illumination = Math.round(Number(moon.illumination_pct) || 0);
      setText("#sky-moon-name", `MOND · ${(moon.phase_name || "–").toUpperCase()}`);
      setText("#sky-moon-light", `${illumination} % beleuchtet`);
      setText("#sky-moon-status", moonUp ? "Über dem Horizont" : "Unter dem Horizont");
      el.querySelector("#sky-moon-status").classList.toggle("sky-below", !moonUp);
      setText("#sky-moonrise", moonrise?.text || "--:--");
      setText("#sky-moonset", moonset?.text || "--:--");
      updateMoonShape(moon.phase_fraction);
    },
  };
}
