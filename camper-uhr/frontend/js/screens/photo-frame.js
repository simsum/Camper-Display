const PHOTO_FRAME_INTERVAL_MS = 8000;
const PHOTO_FRAME_WIDTH = 1480;
const PHOTO_FRAME_HEIGHT = 320;
const PHOTO_FRAME_GAP = 5;
const PHOTO_FRAME_MAX = 5;
const PHOTO_FRAME_GROUPS = {
  panorama: 1,
  landscape: 3,
  square: 4,
  portrait: 5,
};

function photoAspect(photo) {
  const explicit = Number(photo.aspect_ratio);
  const measured = Number(photo.width) / Number(photo.height);
  const value = Number.isFinite(explicit) && explicit > 0 ? explicit : measured;
  return Math.max(.42, Math.min(4.6, Number.isFinite(value) && value > 0 ? value : 16 / 9));
}

function photoFormat(photo) {
  const aspect = photoAspect(photo);
  if (aspect >= 2) return "panorama";
  if (aspect >= 1.05) return "landscape";
  if (aspect >= .95) return "square";
  return "portrait";
}

function packPhotoGroup(photos, maximum) {
  if (!photos.length) return [];
  if (maximum === 1) return photos.map(photo => [photo]);
  const best = Array(photos.length + 1).fill(null);
  best[photos.length] = { cost: 0, pages: [] };
  for (let start = photos.length - 1; start >= 0; start -= 1) {
    for (let count = 1; count <= maximum && start + count <= photos.length; count += 1) {
      const batch = photos.slice(start, start + count);
      const naturalWidth = batch.reduce((sum, photo) => sum + photoAspect(photo) * PHOTO_FRAME_HEIGHT, 0)
        + (count - 1) * PHOTO_FRAME_GAP;
      const ratio = naturalWidth / PHOTO_FRAME_WIDTH;
      let cost = ratio <= 1 ? (1 - ratio) ** 2 : ((ratio - 1) * 2.2) ** 2;
      if (count === 1 && photos.length > 1) cost += 1.2;
      const tail = best[start + count];
      if (!tail) continue;
      cost += tail.cost;
      if (!best[start] || cost < best[start].cost) best[start] = { cost, pages: [batch, ...tail.pages] };
    }
  }
  return best[0].pages;
}

function adaptivePhotoPages(photos) {
  const indexed = photos.map((photo, index) => ({ photo, index }));
  const pages = [];
  Object.entries(PHOTO_FRAME_GROUPS).forEach(([format, maximum]) => {
    const entries = indexed.filter(entry => photoFormat(entry.photo) === format);
    const entryByPhoto = new Map(entries.map(entry => [entry.photo, entry]));
    packPhotoGroup(entries.map(entry => entry.photo), maximum).forEach(batch => {
      pages.push({
        batch,
        order: Math.min(...batch.map(photo => entryByPhoto.get(photo).index)),
      });
    });
  });
  return pages.sort((left, right) => left.order - right.order).map(item => item.batch);
}

function createPhotoFrameScreen(options = {}) {
  const element = document.createElement("div");
  element.className = "screen photo-frame-screen";
  element.innerHTML = `
    <div class="photo-frame-page-background" aria-hidden="true"></div>
    <div class="photo-frame-grid">
      ${Array.from({ length: PHOTO_FRAME_MAX }, () => `<div class="photo-frame-tile"><div class="photo-frame-background" aria-hidden="true"></div><img class="photo-frame-image" alt="Urlaubsfoto"><div class="photo-frame-meta"><span></span><strong></strong></div></div>`).join("")}
    </div>
    <div class="photo-frame-vignette" aria-hidden="true"></div>`;
  const grid = element.querySelector(".photo-frame-grid");
  const pageBackground = element.querySelector(".photo-frame-page-background");
  const tiles = Array.from(element.querySelectorAll(".photo-frame-tile"), tile => ({
    element: tile,
    background: tile.querySelector(".photo-frame-background"),
    image: tile.querySelector(".photo-frame-image"),
    meta: tile.querySelector(".photo-frame-meta"),
    date: tile.querySelector(".photo-frame-meta span"),
    place: tile.querySelector(".photo-frame-meta strong"),
  }));
  let photos = Array.isArray(options.initialPhotos) ? options.initialPhotos.slice() : [];
  let page = 0;
  let shownAt = 0;
  let lastRefresh = 0;
  let disposed = false;
  const fetcher = options.fetcher === undefined ? globalThis.fetch?.bind(globalThis) : options.fetcher;
  const intervalMs = options.intervalMs || PHOTO_FRAME_INTERVAL_MS;

  function paint(now = new Date()) {
    if (!photos.length) return;
    const pages = adaptivePhotoPages(photos);
    page %= pages.length;
    const batch = pages[page];
    const naturalWidths = batch.map(photo => photoAspect(photo) * PHOTO_FRAME_HEIGHT);
    const naturalTotal = naturalWidths.reduce((sum, width) => sum + width, 0) + (batch.length - 1) * PHOTO_FRAME_GAP;
    const scale = Math.min(1, PHOTO_FRAME_WIDTH / naturalTotal);
    const height = PHOTO_FRAME_HEIGHT * scale;
    const widths = naturalWidths.map(width => width * scale);
    grid.style.width = `${widths.reduce((sum, width) => sum + width, 0) + (batch.length - 1) * PHOTO_FRAME_GAP}px`;
    grid.style.height = `${height}px`;
    grid.style.gridTemplateColumns = widths.map(width => `${width}px`).join(" ");
    pageBackground.style.backgroundImage = `url("${String(batch[0].url).replace(/["\\]/g, "")}")`;
    tiles.forEach((tile, tileIndex) => {
      const photo = batch[tileIndex];
      tile.element.style.display = photo ? "block" : "none";
      if (!photo) return;
      if (tile.image.dataset.photoId !== photo.id) {
        tile.image.dataset.photoId = photo.id;
        tile.image.src = photo.url;
        tile.background.style.backgroundImage = `url("${String(photo.url).replace(/["\\]/g, "")}")`;
      }
      const takenAt = Number(photo.taken_at) * 1000;
      tile.date.textContent = Number.isFinite(takenAt)
        ? new Date(takenAt).toLocaleDateString("de-DE", { day: "2-digit", month: "2-digit", year: "numeric" }) : "";
      tile.place.textContent = typeof photo.place === "string" ? photo.place : "";
      tile.meta.style.display = tile.date.textContent || tile.place.textContent ? "flex" : "none";
    });
    element.setAttribute("aria-label", `${batch.length} vollständig sichtbare Urlaubsfotos`);
  }

  async function refresh(force = false) {
    if (!fetcher || disposed || (!force && Date.now() - lastRefresh < 30000)) return;
    lastRefresh = Date.now();
    try {
      const response = await fetcher("/api/photos", { cache: "no-store" });
      if (!response.ok) return;
      const payload = await response.json();
      if (!Array.isArray(payload.photos)) return;
      const currentId = adaptivePhotoPages(photos)[page]?.[0]?.id;
      photos = payload.photos.filter(photo => photo && typeof photo.id === "string" && typeof photo.url === "string");
      const refreshedPages = adaptivePhotoPages(photos);
      page = Math.max(0, refreshedPages.findIndex(batch => batch.some(photo => photo.id === currentId)));
      paint();
    } catch (_) {
      // A temporary backend failure only pauses library refresh.
    }
  }

  if (photos.length) paint();
  else refresh(true);
  return {
    element,
    isAvailable() { return photos.length > 0; },
    nextPage() {
      const pages = adaptivePhotoPages(photos);
      if (!pages.length) return;
      page = (page + 1) % pages.length;
      shownAt = Date.now();
      paint();
    },
    onMount() { shownAt = Date.now(); refresh(true); paint(); },
    onUnmount() { shownAt = 0; },
    onDispose() { disposed = true; tiles.forEach(tile => tile.image.removeAttribute("src")); },
    onTick(_status, _settings, now = new Date()) {
      refresh();
      if (!photos.length) return;
      const timestamp = now.getTime();
      if (!shownAt) shownAt = timestamp;
      if (timestamp - shownAt >= intervalMs) {
        page = (page + 1) % adaptivePhotoPages(photos).length;
        shownAt = timestamp;
        paint(now);
      }
    },
  };
}

if (typeof module !== "undefined") module.exports = { createPhotoFrameScreen, PHOTO_FRAME_INTERVAL_MS, PHOTO_FRAME_GROUPS, adaptivePhotoPages, photoAspect, photoFormat };
