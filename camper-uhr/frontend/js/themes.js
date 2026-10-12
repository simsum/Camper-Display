const NIXIE_THEMES = [
  { id: "flip", label: "Flip", kind: "image", path: "assets/nixie-themes/flip" },
  { id: "blue", label: "Blau", kind: "image", path: "assets/nixie-themes/blue" },
  { id: "blank", label: "Schlicht", kind: "image", path: "assets/nixie-themes/blank" },
];

const NIXIE_ALIGNMENT = {
  blank: {
    width: 136, height: 320, housing: "colon_off", window: [14,68,107,150],
    digits: [[14,68,107,162],[15,72,105,138],[15,69,105,151],[14,68,107,139],[17,70,101,136],[14,70,107,134],[15,67,105,151],[15,72,105,128],[14,68,107,150],[15,70,105,150]],
    colon: [14,68,107,150],
  },
  blue: {
    width: 194, height: 320, housing: "colon_off", window: [29,78,117,165],
    digits: [[40,79,120,157],[55,79,114,151],[40,79,116,163],[29,75,118,165],[26,77,115,156],[40,77,122,155],[54,77,114,164],[41,77,115,159],[29,78,117,165],[27,79,114,164]],
    colon: [29,78,117,165],
  },
};

function getTheme(themeId) {
  return NIXIE_THEMES.find((t) => t.id === themeId) ?? NIXIE_THEMES[0];
}

function themeDigitSrc(theme, digit) {
  return `${theme.path}/${digit}.png`;
}

function themeColonSrc(theme, on) {
  return `${theme.path}/${on ? "colon" : "colon_off"}.png`;
}

function themePreviewSrc(theme) {
  return themeDigitSrc(theme, 5);
}
