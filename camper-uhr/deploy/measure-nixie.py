"""Read existing sprites and print alignment data; never modifies PNG files."""
import json
from pathlib import Path
import numpy as np
from PIL import Image

ROOT = Path(__file__).resolve().parents[1] / "frontend/assets/nixie-themes"
# Interior electrode windows, excluding glass, feet, screws and decorative animals.
WINDOWS = {
    "blank": [[14,67,121,233],[15,70,120,222],[15,68,120,228],[14,67,121,224],[17,68,118,217],[14,68,121,222],[15,67,120,224],[15,70,120,217],[14,67,121,227],[15,68,120,228]],
    "blue": [[40,79,160,241],[55,79,169,241],[40,79,156,243],[29,75,147,242],[26,77,141,241],[40,77,162,240],[54,77,168,241],[41,77,156,244],[29,78,146,243],[27,79,141,243]],
}

result = {}
for name, windows in WINDOWS.items():
    fields = []
    for digit, (left, top, right, bottom) in enumerate(windows):
        pixels = np.asarray(Image.open(ROOT / name / f"{digit}.png").convert("RGBA")).astype(float)
        roi = pixels[top:bottom, left:right]
        bright = (roi[:,:,0] > 185) & (roi[:,:,1] > 80) & (roi[:,:,0] > roi[:,:,1] * 1.15) & (roi[:,:,1] > roi[:,:,2] * 1.6) & (roi[:,:,3] > 180)
        ys, xs = np.where(bright)
        assert len(ys), (name, digit)
        upper = max(top, top + int(ys.min()) - 5)
        lower = min(bottom, top + int(ys.max()) + 6)
        fields.append([left, upper, right-left, lower-upper])
    width, height = Image.open(ROOT / name / "8.png").size
    reference = 8
    # Colons were created from sprite 8 and retain its coordinate system.
    result[name] = {"width":width,"height":height,"housing": "colon_off", "window":fields[reference], "digits":fields, "colon":fields[8]}
print(json.dumps(result, indent=2))
