const VACATION_DAY_MS = 86400000;

function vacationEscape(value) {
  return String(value ?? "")
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;")
    .replaceAll('"', "&quot;")
    .replaceAll("'", "&#039;");
}

function vacationLocalDate(value) {
  const match = typeof value === "string" && value.match(/^(\d{4})-(\d{2})-(\d{2})$/);
  if (!match) return null;
  const date = new Date(Number(match[1]), Number(match[2]) - 1, Number(match[3]));
  return Number.isNaN(date.getTime()) ? null : date;
}

function vacationDayStart(value) {
  return new Date(value.getFullYear(), value.getMonth(), value.getDate());
}

function vacationAddDays(value, days) {
  return new Date(value.getFullYear(), value.getMonth(), value.getDate() + days);
}

function vacationDayDifference(start, end) {
  const startUtc = Date.UTC(start.getFullYear(), start.getMonth(), start.getDate());
  const endUtc = Date.UTC(end.getFullYear(), end.getMonth(), end.getDate());
  return Math.round((endUtc - startUtc) / VACATION_DAY_MS);
}

function vacationClamp(value, minimum, maximum) {
  return Math.max(minimum, Math.min(maximum, value));
}

function vacationFormatDate(value, options) {
  return value.toLocaleDateString("de-DE", options);
}

function vacationFormatRange(start, end) {
  const startDay = String(start.getDate()).padStart(2, "0");
  const endDay = String(end.getDate()).padStart(2, "0");
  const startMonth = vacationFormatDate(start, { month: "long" });
  const endMonth = vacationFormatDate(end, { month: "long" });
  if (start.getFullYear() === end.getFullYear() && start.getMonth() === end.getMonth()) {
    return `${startDay}.–${endDay}. ${endMonth}`;
  }
  const endYear = start.getFullYear() === end.getFullYear() ? "" : ` ${end.getFullYear()}`;
  return `${startDay}. ${startMonth} – ${endDay}. ${endMonth}${endYear}`;
}

function vacationSeasonTransition(year, index) {
  const y = (year - 2000) / 1000;
  const coefficients = [
    [2451623.80984, 365242.37404, 0.05169, -0.00411, -0.00057],
    [2451716.56767, 365241.62603, 0.00325, 0.00888, -0.00030],
    [2451810.21715, 365242.01767, -0.11575, 0.00337, 0.00078],
    [2451900.05952, 365242.74049, -0.06223, -0.00823, 0.00032],
  ][index];
  const jde0 = coefficients[0]
    + coefficients[1] * y
    + coefficients[2] * y ** 2
    + coefficients[3] * y ** 3
    + coefficients[4] * y ** 4;
  const t = (jde0 - 2451545.0) / 36525;
  const radians = (degrees) => degrees * Math.PI / 180;
  const w = radians(35999.373 * t - 2.47);
  const deltaLambda = 1 + 0.0334 * Math.cos(w) + 0.0007 * Math.cos(2 * w);
  const terms = [
    [485,324.96,1934.136],[203,337.23,32964.467],[199,342.08,20.186],
    [182,27.85,445267.112],[156,73.14,45036.886],[136,171.52,22518.443],
    [77,222.54,65928.934],[74,296.72,3034.906],[70,243.58,9037.513],
    [58,119.81,33718.147],[52,297.17,150.678],[50,21.02,2281.226],
    [45,247.54,29929.562],[44,325.15,31555.956],[29,60.93,4443.417],
    [18,155.12,67555.328],[17,288.79,4562.452],[16,198.04,62894.029],
    [14,199.76,31436.921],[12,95.39,14577.848],[12,287.11,31931.756],
    [12,320.81,34777.259],[9,227.73,1222.114],[8,15.45,16859.074],
  ];
  const correction = terms.reduce(
    (sum, [amplitude, phase, frequency]) => sum + amplitude * Math.cos(radians(phase + frequency * t)),
    0,
  );
  const julianDay = jde0 + 0.00001 * correction / deltaLambda;
  return new Date((julianDay - 2440587.5) * VACATION_DAY_MS);
}

function vacationSeasonInfo(now) {
  const year = now.getFullYear();
  const transitions = [0, 1, 2, 3].map((index) => vacationSeasonTransition(year, index));
  let name = "Winter";
  if (now >= transitions[0] && now < transitions[1]) name = "Frühling";
  else if (now >= transitions[1] && now < transitions[2]) name = "Sommer";
  else if (now >= transitions[2] && now < transitions[3]) name = "Herbst";
  return { name, transitions };
}

function vacationNormalizeTrips(settings, calendar = {}) {
  const combined = [...(settings?.vacations || []), ...(calendar.enabled ? calendar.vacations || [] : [])];
  const seen = new Set();
  return combined
    .filter((item) => item.enabled)
    .filter((item) => {
      const key = JSON.stringify([item.name.trim().toLowerCase(), item.start_date, item.end_date, (item.destination || "").trim().toLowerCase()]);
      if (seen.has(key)) return false;
      seen.add(key);
      return true;
    })
    .map((item) => ({ ...item, start: vacationLocalDate(item.start_date), end: vacationLocalDate(item.end_date) }))
    .filter((item) => item.start && item.end && item.end >= item.start)
    .sort((a, b) => a.start - b.start);
}

function vacationDateCard(now, seasonName) {
  const dayOfYear = vacationDayDifference(new Date(now.getFullYear(), 0, 1), vacationDayStart(now)) + 1;
  const weekNumberDate = new Date(Date.UTC(now.getFullYear(), now.getMonth(), now.getDate()));
  const weekDay = weekNumberDate.getUTCDay() || 7;
  weekNumberDate.setUTCDate(weekNumberDate.getUTCDate() + 4 - weekDay);
  const yearStart = new Date(Date.UTC(weekNumberDate.getUTCFullYear(), 0, 1));
  const week = Math.ceil((((weekNumberDate - yearStart) / VACATION_DAY_MS) + 1) / 7);
  return `
    <section class="vacation-glass vacation-date-card">
      <div class="vacation-eyebrow">HEUTE</div>
      <div class="vacation-weekday">${vacationFormatDate(now, { weekday: "long" })}</div>
      <div class="vacation-date-main">
        <div class="vacation-day">${String(now.getDate()).padStart(2, "0")}</div>
        <div class="vacation-month-year">
          <div class="vacation-month">${vacationFormatDate(now, { month: "long" })}</div>
          <div class="vacation-year">${now.getFullYear()}</div>
        </div>
      </div>
      <div class="vacation-season-note">
        <div class="vacation-season-note-title">KALENDERWOCHE ${week}</div>
        <div class="vacation-season-note-copy">${seasonName} · ${dayOfYear}. Tag</div>
      </div>
    </section>`;
}

function vacationCamperMarker() {
  return `<div class="vacation-camper"><span></span></div>`;
}

function vacationRenderActive(now, trip, dateCard) {
  const endExclusive = vacationAddDays(trip.end, 1);
  const totalDays = vacationDayDifference(trip.start, trip.end) + 1;
  const dayNumber = vacationClamp(vacationDayDifference(trip.start, vacationDayStart(now)) + 1, 1, totalDays);
  const progress = vacationClamp((now - trip.start) / (endExclusive - trip.start) * 100, 0, 100);
  const remaining = Math.max(0, vacationDayDifference(vacationDayStart(now), trip.end));
  const startedDays = Math.max(0, vacationDayDifference(trip.start, vacationDayStart(now)));
  const destination = trip.destination
    ? `<div class="vacation-trip-destination">⌖ ${vacationEscape(trip.destination)}</div>`
    : "";
  return `
    <div class="vacation-scene">
      ${dateCard}
      <section class="vacation-glass vacation-trip-card">
        <div class="vacation-trip-top">
          <div><div class="vacation-eyebrow">UNSER URLAUB</div><div class="vacation-trip-title">${vacationEscape(trip.name)}</div>${destination}</div>
          <div class="vacation-trip-range">URLAUBSZEIT<b>${vacationFormatRange(trip.start, trip.end)}</b></div>
        </div>
        <div class="vacation-timeline">
          <div class="vacation-track"><div class="vacation-track-fill" style="width:${progress.toFixed(2)}%"></div></div>
          <div class="vacation-track-start"></div><div class="vacation-track-end"></div>
          <div class="vacation-marker" style="left:${progress.toFixed(2)}%">${vacationCamperMarker()}<div class="vacation-today-pill">HEUTE</div></div>
          <div class="vacation-timeline-label vacation-label-start"><b>${vacationFormatDate(trip.start, { day: "2-digit", month: "short" }).toUpperCase()}</b><br>Start</div>
          <div class="vacation-timeline-label vacation-label-end"><b>${vacationFormatDate(trip.end, { day: "2-digit", month: "short" }).toUpperCase()}</b><br>Ende</div>
        </div>
        <div class="vacation-trip-footer"><span>Begonnen vor <b>${startedDays} ${startedDays === 1 ? "Tag" : "Tagen"}</b></span><span>Fortschritt ausschließlich nach Zeit</span></div>
      </section>
      <section class="vacation-glass vacation-progress-card">
        <div class="vacation-progress-top">
          <div class="vacation-ring" style="--progress:${progress.toFixed(2)}%"><div>${Math.round(progress)} %</div></div>
          <div class="vacation-progress-copy"><div class="vacation-eyebrow">URLAUB</div><div class="vacation-progress-big">Tag ${dayNumber}<br>von ${totalDays}</div><div class="vacation-progress-small">Zeitlicher Fortschritt</div></div>
        </div>
        <div class="vacation-stats">
          <div class="vacation-stat"><div class="vacation-stat-label">NOCH</div><div class="vacation-stat-value">${remaining}</div><div class="vacation-stat-unit">${remaining === 1 ? "Tag" : "Tage"}</div></div>
          <div class="vacation-stat"><div class="vacation-stat-label">ENDE</div><div class="vacation-stat-value">${String(trip.end.getDate()).padStart(2, "0")}.</div><div class="vacation-stat-unit">${vacationFormatDate(trip.end, { month: "long" })}</div></div>
        </div>
      </section>
    </div>`;
}

function vacationSeasonSegments(year, transitions) {
  const start = new Date(year, 0, 1);
  const end = new Date(year + 1, 0, 1);
  const points = [start, ...transitions, end];
  const names = ["❄ WINTER", "✿ FRÜHLING", "☀ SOMMER", "◆ HERBST", "❄"];
  const classes = ["winter", "spring", "summer", "autumn", "winter vacation-winter-tail"];
  return names.map((name, index) => {
    const width = (points[index + 1] - points[index]) / (end - start) * 100;
    let detail = "";
    if (index === 0) detail = `bis ${vacationFormatDate(transitions[0], { day: "numeric", month: "long" })}`;
    else if (index < 4) detail = `${vacationFormatDate(points[index], { day: "numeric", month: "short" })} – ${vacationFormatDate(points[index + 1], { day: "numeric", month: "short" })}`;
    return `<div class="vacation-season vacation-${classes[index]}" style="width:${width.toFixed(4)}%">${name}${detail ? `<small>${detail}</small>` : ""}</div>`;
  }).join("");
}

function vacationRenderYear(now, trips, dateCard, seasonInfo) {
  const year = now.getFullYear();
  const yearStart = new Date(year, 0, 1);
  const yearEnd = new Date(year + 1, 0, 1);
  const today = vacationDayStart(now);
  const yearProgress = vacationClamp((now - yearStart) / (yearEnd - yearStart) * 100, 0, 100);
  const dayNumber = vacationDayDifference(yearStart, today) + 1;
  const daysInYear = vacationDayDifference(yearStart, yearEnd);
  const nextTrip = trips.find((trip) => trip.start > today) || null;
  const nextDays = nextTrip ? vacationDayDifference(today, nextTrip.start) : null;
  const yearTrips = trips.filter((trip) => vacationAddDays(trip.end, 1) > yearStart && trip.start < yearEnd);
  const bars = yearTrips.map((trip, index) => {
    const clippedStart = new Date(Math.max(trip.start, yearStart));
    const clippedEnd = new Date(Math.min(vacationAddDays(trip.end, 1), yearEnd));
    const left = (clippedStart - yearStart) / (yearEnd - yearStart) * 100;
    const width = Math.max(1.1, (clippedEnd - clippedStart) / (yearEnd - yearStart) * 100);
    const kind = nextTrip?.id === trip.id ? "next" : trip.end < today ? "past" : "future";
    return `<div class="vacation-year-trip vacation-trip-${kind}" style="left:${left.toFixed(3)}%;width:${width.toFixed(3)}%;top:${index % 2 === 0 ? -9 : 7}px"></div>`;
  }).join("");
  const legendShown = yearTrips.slice(0, 4);
  const legend = legendShown.map((trip) => {
    const kind = nextTrip?.id === trip.id ? "next" : trip.end < today ? "past" : "future";
    return `<span class="vacation-legend-item"><i class="vacation-legend-dot vacation-legend-${kind}"></i>${vacationEscape(trip.name)}${kind === "next" ? " · als Nächstes" : ""}</span>`;
  }).join("");
  const more = yearTrips.length > 4 ? `<span class="vacation-legend-more">+${yearTrips.length - 4} weitere</span>` : "";
  const nextPanel = nextTrip ? `
    <div class="vacation-countdown-top">
      <div class="vacation-count-ring" style="--year-progress:${yearProgress.toFixed(2)}%"><div class="vacation-count-value"><b>${nextDays}</b><span>${nextDays === 1 ? "TAG" : "TAGE"}</span></div></div>
      <div class="vacation-next-copy"><div class="vacation-eyebrow">NÄCHSTER URLAUB</div><div class="vacation-next-big">${vacationEscape(nextTrip.name)}</div><div class="vacation-next-small">Start am ${vacationFormatDate(nextTrip.start, { day: "numeric", month: "long" })}</div>${nextTrip.destination ? `<div class="vacation-next-destination">⌖ ${vacationEscape(nextTrip.destination)}</div>` : ""}</div>
    </div>
    <div class="vacation-stats">
      <div class="vacation-stat"><div class="vacation-stat-label">START</div><div class="vacation-stat-value">${String(nextTrip.start.getDate()).padStart(2, "0")}.</div><div class="vacation-stat-unit">${vacationFormatDate(nextTrip.start, { month: "long" })}</div></div>
      <div class="vacation-stat"><div class="vacation-stat-label">DAUER</div><div class="vacation-stat-value">${vacationDayDifference(nextTrip.start, nextTrip.end) + 1}</div><div class="vacation-stat-unit">Tage</div></div>
    </div>` : `
    <div class="vacation-no-next"><div class="vacation-no-next-icon">＋</div><div class="vacation-eyebrow">NÄCHSTER URLAUB</div><div class="vacation-next-big">Noch keiner geplant</div><div class="vacation-next-small">In den Einstellungen hinzufügen</div></div>`;
  return `
    <div class="vacation-scene">
      ${dateCard}
      <section class="vacation-glass vacation-year-card">
        <div class="vacation-year-top"><div><div class="vacation-eyebrow">JAHRESREISE</div><div class="vacation-year-title">Das Jahr ${year}</div></div><div class="vacation-year-day">JAHRESFORTSCHRITT<b>Tag ${dayNumber} von ${daysInYear}</b></div></div>
        <div class="vacation-seasons">${vacationSeasonSegments(year, seasonInfo.transitions)}</div>
        <div class="vacation-year-line">
          <div class="vacation-year-track"><div class="vacation-year-elapsed" style="width:${yearProgress.toFixed(2)}%"></div></div>
          ${bars}
          <div class="vacation-year-today" style="left:${yearProgress.toFixed(2)}%"><div></div><span>HEUTE</span></div>
          <div class="vacation-months"><span>JAN</span><span>FEB</span><span>MÄR</span><span>APR</span><span>MAI</span><span>JUN</span><span>JUL</span><span>AUG</span><span>SEP</span><span>OKT</span><span>NOV</span><span>DEZ</span></div>
        </div>
        <div class="vacation-legend">${legend || '<span class="vacation-legend-empty">Noch keine Urlaubszeiten in diesem Jahr</span>'}${more}<span class="vacation-legend-note">Urlaubszeiten im Jahr</span></div>
      </section>
      <section class="vacation-glass vacation-countdown-card">${nextPanel}</section>
    </div>`;
}

function createCalendarScreen() {
  const element = document.createElement("div");
  element.className = "screen vacation-screen";
  let lastKey = "";

  function update(status, settings) {
    const now = new Date(status?.server_time_iso || Date.now());
    const calendar = status?.calendar || {};
    const trips = vacationNormalizeTrips(settings, calendar);
    const key = `${now.getFullYear()}-${now.getMonth()}-${now.getDate()}-${now.getHours()}-${now.getMinutes()}-${JSON.stringify(trips)}-${calendar.state}-${calendar.stale}`;
    if (key === lastKey) return;
    lastKey = key;
    const today = vacationDayStart(now);
    const active = trips.find((trip) => trip.start <= today && trip.end >= today) || null;
    const seasonInfo = vacationSeasonInfo(now);
    const dateCard = vacationDateCard(now, seasonInfo.name);
    element.innerHTML = active
      ? vacationRenderActive(now, active, dateCard)
      : vacationRenderYear(now, trips, dateCard, seasonInfo);
    if (calendar.enabled && (calendar.stale || calendar.state === "error" || calendar.state === "loading")) {
      const note = document.createElement("div");
      note.className = "vacation-sync-note";
      note.textContent = calendar.stale ? "iCloud · gespeicherter Stand"
        : calendar.state === "loading" ? "iCloud · wird geladen" : "iCloud · nicht verfügbar";
      element.appendChild(note);
    }
  }

  return {
    element,
    onMount() {},
    onTick: update,
    isAvailable() { return true; },
  };
}
