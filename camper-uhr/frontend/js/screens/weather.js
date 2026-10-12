const WEATHER_CODE_TEXT = {
  0: "Klar", 1: "Meist klar", 2: "Wolken & Sonne", 3: "Bewölkt",
  45: "Nebel", 48: "Raureifnebel", 51: "Leichter Niesel", 53: "Nieselregen",
  55: "Starker Niesel", 56: "Gefrierender Niesel", 57: "Gefrierender Niesel",
  61: "Leichter Regen", 63: "Regen", 65: "Starkregen", 66: "Gefrierender Regen",
  67: "Gefrierender Regen", 71: "Leichter Schnee", 73: "Schnee", 75: "Starker Schnee",
  77: "Schneegriesel", 80: "Regenschauer", 81: "Regenschauer", 82: "Starke Schauer",
  85: "Schneeschauer", 86: "Starke Schneeschauer", 95: "Gewitter",
  96: "Gewitter mit Hagel", 99: "Starkes Gewitter",
};

const WEATHER_CODE_ICON = {
  0: "☀️", 1: "🌤️", 2: "⛅", 3: "☁️", 45: "🌫️", 48: "🌫️",
  51: "🌦️", 53: "🌦️", 55: "🌧️", 56: "🌧️", 57: "🌧️",
  61: "🌦️", 63: "🌧️", 65: "🌧️", 66: "🌧️", 67: "🌧️",
  71: "🌨️", 73: "🌨️", 75: "❄️", 77: "❄️", 80: "🌦️",
  81: "🌧️", 82: "🌧️", 85: "🌨️", 86: "❄️", 95: "⛈️", 96: "⛈️", 99: "⛈️",
};

const WEATHER_WEEKDAY = new Intl.DateTimeFormat("de-DE", { weekday: "long" });
const WEATHER_DECIMAL = new Intl.NumberFormat("de-DE", {
  minimumFractionDigits: 1,
  maximumFractionDigits: 1,
});

function createWeatherScreen() {
  const el = document.createElement("div");
  el.className = "screen weather-screen";
  el.innerHTML = `
    <div class="weather-scene">
      <section class="weather-current">
        <div class="weather-eyebrow" id="weather-eyebrow">Jetzt</div>
        <div class="weather-current-main">
          <div class="weather-current-temp" id="weather-current-temp">--°</div>
          <div class="weather-current-condition">
            <strong id="weather-current-condition">Keine Daten</strong>
            <span id="weather-feels-like">Gefühlt --°</span>
          </div>
        </div>
        <div class="weather-current-details">
          <div class="weather-detail"><small>Regen</small><b id="weather-current-rain">-- %</b></div>
          <div class="weather-detail"><small>Wind</small><b id="weather-current-wind">-- km/h</b></div>
        </div>
      </section>
      <div class="weather-location"><span class="weather-place">Wetterstandort unbekannt</span><a class="weather-place-source" href="https://www.openstreetmap.org/copyright" target="_blank" rel="noopener" hidden>© OpenStreetMap</a></div>
      <section class="weather-forecast" id="weather-forecast" aria-label="Wettervorhersage"></section>
    </div>
  `;

  let lastWeatherJson = "";

  function dayLabel(day, index) {
    if (index === 0) return "Heute";
    return WEATHER_WEEKDAY.format(new Date(`${day.date}T12:00:00`));
  }

  function rounded(value, fallback = "–") {
    return Number.isFinite(value) ? String(Math.round(value)) : fallback;
  }

  function rainAmount(value) {
    return Number.isFinite(value) ? WEATHER_DECIMAL.format(value) : "–";
  }

  function render(weather) {
    const place = el.querySelector(".weather-place");
    const coordinates = Number.isFinite(weather.latitude) && Number.isFinite(weather.longitude)
      ? `${weather.latitude.toFixed(3)}°, ${weather.longitude.toFixed(3)}°` : null;
    place.textContent = weather.location_name || coordinates || "Wetterstandort unbekannt";
    place.title = [weather.location_name, coordinates ? `Wetterabruf für ${coordinates}` : null].filter(Boolean).join(" · ");
    el.querySelector(".weather-place-source").hidden = !weather.location_name;
    const today = weather.forecast?.[0] || {};
    const unit = weather.unit_celsius ? "°" : "°F";
    const todayDate = today.date ? new Date(`${today.date}T12:00:00`) : new Date();
    const weekday = WEATHER_WEEKDAY.format(todayDate);

    el.querySelector("#weather-eyebrow").textContent = `Jetzt · ${weekday}`;
    el.querySelector("#weather-current-temp").textContent = `${rounded(weather.temperature)}${unit}`;
    el.querySelector("#weather-current-condition").textContent =
      WEATHER_CODE_TEXT[weather.condition_code] ?? "Unbekannt";
    el.querySelector("#weather-feels-like").textContent =
      `Gefühlt ${rounded(weather.apparent_temperature)}${unit}`;
    el.querySelector("#weather-current-rain").textContent =
      `${rounded(today.precipitation_probability)} %`;
    el.querySelector("#weather-current-wind").textContent =
      `${rounded(weather.wind_speed)} km/h`;

    const forecast = el.querySelector("#weather-forecast");
    forecast.innerHTML = "";
    weather.forecast.slice(0, 4).forEach((day, index) => {
      const card = document.createElement("article");
      card.className = `weather-day${index === 0 ? " weather-day-today" : ""}`;
      card.innerHTML = `
        <div class="weather-day-name">${dayLabel(day, index)}</div>
        <div class="weather-day-icon">${WEATHER_CODE_ICON[day.condition_code] ?? "🌡️"}</div>
        <div class="weather-day-range">
          <span class="weather-day-high">${rounded(day.temp_max)}${unit}</span>
          <span class="weather-day-low">${rounded(day.temp_min)}${unit}</span>
        </div>
        <div class="weather-day-rain">
          <span class="weather-day-rain-probability">💧 ${rounded(day.precipitation_probability)} %</span>
          <span class="weather-day-rain-amount">${rainAmount(day.precipitation_sum)} mm Regen</span>
        </div>
      `;
      forecast.appendChild(card);
    });
  }

  return {
    element: el,
    isAvailable(status) {
      return Boolean(status?.weather?.available && status.weather.forecast?.length);
    },
    onMount() {},
    onTick(status) {
      const weather = status.weather;
      if (!weather?.available) return;
      const weatherJson = JSON.stringify(weather);
      if (weatherJson === lastWeatherJson) return;
      lastWeatherJson = weatherJson;
      render(weather);
    },
  };
}
