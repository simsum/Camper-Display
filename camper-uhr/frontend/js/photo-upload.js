const input = document.getElementById("photo-input");
const progress = document.getElementById("progress");
const grid = document.getElementById("photos");
const count = document.getElementById("count");
const presentationDuration = document.getElementById("photo-frame-duration");
const presentationStatus = document.getElementById("photo-frame-status");

function sameOriginHeaders(type) {
  return { "Content-Type": type };
}

function uploadHeaders(type, metadata) {
  const headers = sameOriginHeaders(type);
  if (Number.isFinite(metadata.takenAt)) headers["X-Photo-Taken-At"] = String(metadata.takenAt);
  if (Number.isFinite(metadata.latitude) && Number.isFinite(metadata.longitude)) {
    headers["X-Photo-Latitude"] = String(metadata.latitude);
    headers["X-Photo-Longitude"] = String(metadata.longitude);
  }
  return headers;
}

async function photoBlob(file) {
  const source = URL.createObjectURL(file);
  try {
    const image = new Image();
    image.src = source;
    await image.decode();
    const maxWidth = 1920, maxHeight = 1280;
    const scale = Math.min(1, maxWidth / image.naturalWidth, maxHeight / image.naturalHeight);
    const canvas = document.createElement("canvas");
    canvas.width = Math.max(1, Math.round(image.naturalWidth * scale));
    canvas.height = Math.max(1, Math.round(image.naturalHeight * scale));
    canvas.getContext("2d", { alpha: false }).drawImage(image, 0, 0, canvas.width, canvas.height);
    return await new Promise((resolve, reject) => canvas.toBlob(
      blob => blob ? resolve(blob) : reject(new Error("Foto konnte nicht vorbereitet werden")),
      "image/jpeg", .88,
    ));
  } finally {
    URL.revokeObjectURL(source);
  }
}

async function loadPhotos() {
  const response = await fetch("/api/photos", { cache: "no-store" });
  if (!response.ok) throw new Error("Fotoliste nicht verfügbar");
  const payload = await response.json();
  count.textContent = `${payload.count} ${payload.count === 1 ? "Foto" : "Fotos"}`;
  grid.replaceChildren();
  if (!payload.photos.length) {
    const empty = document.createElement("div");
    empty.className = "empty";
    empty.textContent = "Noch keine Fotos übertragen.";
    grid.appendChild(empty);
    return;
  }
  for (const photo of payload.photos) {
    const card = document.createElement("div");
    card.className = "photo";
    const image = document.createElement("img");
    image.src = photo.url;
    image.alt = "Gespeichertes Urlaubsfoto";
    image.loading = "lazy";
    const remove = document.createElement("button");
    remove.type = "button";
    remove.textContent = "×";
    remove.setAttribute("aria-label", "Foto löschen");
    remove.addEventListener("click", async () => {
      if (remove.dataset.confirm !== "true") {
        remove.dataset.confirm = "true";
        remove.textContent = "Löschen?";
        remove.classList.add("confirm-delete");
        remove.setAttribute("aria-label", "Löschen bestätigen");
        progress.textContent = "Zum Löschen bitte noch einmal auf „Löschen?“ tippen.";
        return;
      }
      remove.disabled = true;
      progress.textContent = "Foto wird gelöscht …";
      try {
        const response = await fetch("/api/photos/delete", {
          method: "POST", headers: sameOriginHeaders("application/json"), body: JSON.stringify({ id: photo.id }),
        });
        const body = await response.json().catch(() => ({}));
        if (!response.ok) throw new Error(body.detail || "Foto konnte nicht gelöscht werden");
        await loadPhotos();
        progress.textContent = "Foto wurde gelöscht.";
      } catch (error) {
        remove.disabled = false;
        remove.dataset.confirm = "false";
        remove.textContent = "×";
        remove.classList.remove("confirm-delete");
        remove.setAttribute("aria-label", "Foto löschen");
        progress.textContent = error.message || "Foto konnte nicht gelöscht werden.";
      }
    });
    card.append(image, remove);
    grid.appendChild(card);
  }
}

async function loadPresentationSettings() {
  const response = await fetch("/api/settings", { cache: "no-store" });
  if (!response.ok) throw new Error("Einstellungen nicht verfügbar");
  const settings = await response.json();
  presentationDuration.value = settings.photo_frame_manual_seconds ?? 300;
  return settings;
}

async function updatePresentationStatus() {
  try {
    const response = await fetch("/api/photos/status", { cache: "no-store" });
    if (!response.ok) throw new Error();
    const state = await response.json();
    if (!state.active) {
      presentationStatus.textContent = "Nicht aktiv.";
      return;
    }
    const minutes = Math.floor(state.remaining_seconds / 60);
    const seconds = String(state.remaining_seconds % 60).padStart(2, "0");
    presentationStatus.textContent = `Aktiv · noch ${minutes}:${seconds} Minuten`;
  } catch {
    presentationStatus.textContent = "Status momentan nicht verfügbar.";
  }
}

async function setPresentation(active) {
  try {
    if (active) {
      if (!presentationDuration.checkValidity()) {
        presentationDuration.reportValidity();
        return;
      }
      const seconds = Number(presentationDuration.value);
      const settings = await loadPresentationSettings();
      settings.photo_frame_manual_seconds = seconds;
      presentationDuration.value = seconds;
      const saved = await fetch("/api/settings", {
        method: "PUT",
        headers: sameOriginHeaders("application/json"),
        body: JSON.stringify(settings),
      });
      if (!saved.ok) throw new Error("Anzeigedauer konnte nicht gespeichert werden");
    }
    const response = await fetch(`/api/photos/${active ? "show" : "hide"}`, {
      method: "POST",
      headers: sameOriginHeaders("application/json"),
      body: "{}",
    });
    const body = await response.json().catch(() => ({}));
    if (!response.ok) throw new Error(body.detail || "Reisemomente konnten nicht geschaltet werden");
    await updatePresentationStatus();
  } catch (error) {
    presentationStatus.textContent = error.message || "Reisemomente konnten nicht geschaltet werden.";
  }
}

input.addEventListener("change", async () => {
  const files = [...input.files];
  input.value = "";
  for (let index = 0; index < files.length; index += 1) {
    progress.textContent = `Foto ${index + 1} von ${files.length} wird vorbereitet …`;
    try {
      const metadata = await extractPhotoMetadata(files[index]);
      const blob = await photoBlob(files[index]);
      const response = await fetch("/api/photos/upload", {
        method: "POST", headers: uploadHeaders(blob.type, metadata), body: blob,
      });
      if (!response.ok) {
        const body = await response.json().catch(() => ({}));
        throw new Error(body.detail || "Upload fehlgeschlagen");
      }
    } catch (error) {
      progress.textContent = `${files[index].name}: ${error.message || "nicht unterstützt"}`;
      return;
    }
  }
  progress.textContent = `${files.length} ${files.length === 1 ? "Foto wurde" : "Fotos wurden"} übertragen.`;
  await loadPhotos();
});

document.getElementById("photo-frame-show").addEventListener("click", () => setPresentation(true));
document.getElementById("photo-frame-hide").addEventListener("click", () => setPresentation(false));

loadPhotos().catch(error => { progress.textContent = error.message; });
loadPresentationSettings().catch(error => { presentationStatus.textContent = error.message; });
updatePresentationStatus();
setInterval(updatePresentationStatus, 1000);
