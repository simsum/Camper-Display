function renderAlignedNixieTubes(container, digitCount, theme, geometry) {
  container.replaceChildren();
  const row = document.createElement("div");
  row.className = "nixie-row nixie-img-row nixie-aligned-row";
  row.style.setProperty("--nixie-slot-width", `${geometry.width * 280 / geometry.height}px`);
  const digits = [];
  const colons = [];

  function createTube(isColon) {
    const tube = document.createElement("span");
    tube.className = `nixie-aligned-tube nixie-aligned-${theme.id}`;
    const housing = document.createElement("img");
    housing.className = "nixie-aligned-housing";
    housing.alt = "";
    housing.src = themeDigitSrc(theme, geometry.housing);
    tube.appendChild(housing);
    const field = document.createElement("span");
    field.className = "nixie-aligned-window";
    const [x, y, w, h] = geometry.window;
    Object.assign(field.style, {
      left: `${x / geometry.width * 100}%`, top: `${y / geometry.height * 100}%`,
      width: `${w / geometry.width * 100}%`, height: `${h / geometry.height * 100}%`,
    });
    const layers = new Map();
    const symbols = isColon ? ["colon", "colon_off"] : Array.from({ length: 10 }, (_, i) => String(i));
    // All numeral layers load once. Only visibility changes when time advances.
    for (const symbol of symbols) {
      const crop = isColon ? geometry.colon : geometry.digits[Number(symbol)];
      const image = document.createElement("img");
      image.className = "nixie-aligned-numeral";
      image.alt = "";
      image.src = themeDigitSrc(theme, symbol);
      const [sx, sy, sw, sh] = crop;
      Object.assign(image.style, {
        width: `${geometry.width / sw * 100}%`, height: `${geometry.height / sh * 100}%`,
        left: `${-sx / sw * 100}%`, top: `${-sy / sh * 100}%`,
      });
      field.appendChild(image);
      layers.set(symbol, image);
    }
    let wanted = null;
    let visible = null;
    tube.showSymbol = (symbol) => {
      wanted = String(symbol);
      const image = layers.get(wanted);
      if (!image) return;
      const show = () => {
        if (layers.get(wanted) !== image) return;
        if (visible) visible.style.visibility = "hidden";
        image.style.visibility = "visible";
        visible = image;
        tube.setAttribute("aria-label", isColon ? ":" : wanted);
      };
      if (image.complete && image.naturalWidth) show();
      else image.addEventListener("load", show, { once: true });
    };
    tube.appendChild(field);
    row.appendChild(tube);
    tube.showSymbol(isColon ? "colon" : "0");
    return tube;
  }

  for (let index = 0; index < digitCount; index += 1) {
    digits.push(createTube(false));
    if (index === 1 || index === 3) colons.push(createTube(true));
  }
  container.appendChild(row);
  return {
    aligned: true,
    digitEls: digits,
    setDigit(tube, value) { tube.showSymbol(value); },
    setColonOn(on) { colons.forEach((tube) => tube.showSymbol(on ? "colon" : "colon_off")); },
  };
}

function renderClockTubesImage(container, digitCount, theme) {
  const geometry = NIXIE_ALIGNMENT[theme.id];
  if (geometry) return renderAlignedNixieTubes(container, digitCount, theme, geometry);
  container.innerHTML = "";
  const row = document.createElement("div");
  row.className = "nixie-row nixie-img-row";
  const colonEls = [];
  for (let i = 0; i < digitCount; i++) {
    const tube = document.createElement("span");
    tube.className = "nixie-img-tube";
    const img = document.createElement("img");
    img.className = "nixie-img-digit";
    img.src = themeDigitSrc(theme, 0);
    tube.appendChild(img);
    row.appendChild(tube);
    if (i === 1 || i === 3) {
      const colonTube = document.createElement("span");
      colonTube.className = "nixie-img-tube nixie-img-colon-tube";
      const colonImg = document.createElement("img");
      colonImg.className = "nixie-img-digit nixie-img-colon";
      colonImg.src = themeColonSrc(theme, true);
      colonTube.appendChild(colonImg);
      row.appendChild(colonTube);
      colonEls.push(colonImg);
    }
  }
  container.appendChild(row);
  return {
    digitEls: Array.from(row.querySelectorAll(".nixie-img-digit:not(.nixie-img-colon)")),
    setDigit(el, value) {
      el.src = themeDigitSrc(theme, value);
    },
    setColonOn(on) {
      colonEls.forEach((el) => {
        el.src = themeColonSrc(theme, on);
      });
    },
  };
}

function createClockScreen(settings, fixedThemeId) {
  const el = document.createElement("div");
  el.className = "screen";
  const tubesContainer = document.createElement("div");
  el.appendChild(tubesContainer);

  const theme = getTheme(fixedThemeId || settings?.theme);
  el.style.background = settings?.theme_background_colors?.[theme.id] || "#000000";
  const renderer = renderClockTubesImage(tubesContainer, 6, theme);

  let lastValues = ["0", "0", "0", "0", "0", "0"];
  let lastBlink = null;

  function update(currentSettings, now = new Date()) {
    let hours = now.getHours();
    if (!currentSettings.time_format_24h) {
      hours = hours % 12;
      if (hours === 0) hours = 12;
    }
    const values = [
      String(hours).padStart(2, "0")[0],
      String(hours).padStart(2, "0")[1],
      String(now.getMinutes()).padStart(2, "0")[0],
      String(now.getMinutes()).padStart(2, "0")[1],
      String(now.getSeconds()).padStart(2, "0")[0],
      String(now.getSeconds()).padStart(2, "0")[1],
    ];
    values.forEach((value, i) => {
      if (value !== lastValues[i]) {
        const target = renderer.digitEls[i];
        renderer.setDigit(target, value);
        if (!renderer.aligned) {
          target.classList.remove("changing");
          void target.offsetWidth;
          target.classList.add("changing");
        }
        lastValues[i] = value;
      }
    });

    const blinkOn = now.getSeconds() % 2 === 0;
    if (blinkOn !== lastBlink) {
      renderer.setColonOn(blinkOn);
      lastBlink = blinkOn;
    }
  }

  return {
    element: el,
    isClock: true,
    themeId: theme.id,
    onMount() { update(settings); },
    onTick(_status, currentSettings, now) {
      update(currentSettings, now);
    },
  };
}
