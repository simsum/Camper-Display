function parseExifDate(value) {
  const match = /^(\d{4}):(\d{2}):(\d{2})[ T](\d{2}):(\d{2}):(\d{2})/.exec(value || "");
  if (!match) return null;
  const date = new Date(Number(match[1]), Number(match[2]) - 1, Number(match[3]), Number(match[4]), Number(match[5]), Number(match[6]));
  const seconds = date.getTime() / 1000;
  return Number.isFinite(seconds) ? seconds : null;
}

function parseJpegExif(buffer) {
  const view = new DataView(buffer);
  const length = view.byteLength;
  if (length < 4 || view.getUint16(0, false) !== 0xffd8) return {};
  let offset = 2;
  while (offset + 4 <= length) {
    if (view.getUint8(offset) !== 0xff) break;
    const marker = view.getUint8(offset + 1);
    offset += 2;
    if (marker === 0xd9 || marker === 0xda) break;
    if (offset + 2 > length) break;
    const segmentLength = view.getUint16(offset, false);
    if (segmentLength < 2 || offset + segmentLength > length) break;
    const start = offset + 2;
    if (marker === 0xe1 && segmentLength >= 14
        && String.fromCharCode(...new Uint8Array(buffer, start, 6)) === "Exif\0\0") {
      return parseTiffExif(view, start + 6);
    }
    offset += segmentLength;
  }
  return {};
}

function parseTiffExif(view, tiff) {
  if (tiff + 8 > view.byteLength) return {};
  const order = view.getUint16(tiff, false);
  if (order !== 0x4949 && order !== 0x4d4d) return {};
  const little = order === 0x4949;
  const u16 = position => position + 2 <= view.byteLength ? view.getUint16(position, little) : null;
  const u32 = position => position + 4 <= view.byteLength ? view.getUint32(position, little) : null;
  if (u16(tiff + 2) !== 42) return {};
  const sizes = { 1: 1, 2: 1, 3: 2, 4: 4, 5: 8, 7: 1 };

  function entries(relativeOffset) {
    if (!Number.isInteger(relativeOffset) || relativeOffset <= 0) return new Map();
    const base = tiff + Number(relativeOffset);
    const count = u16(base);
    if (!Number.isInteger(count) || count < 0 || count > 256 || base + 2 + count * 12 > view.byteLength) return new Map();
    const result = new Map();
    for (let index = 0; index < count; index += 1) {
      const position = base + 2 + index * 12;
      const tag = u16(position), type = u16(position + 2), itemCount = u32(position + 4);
      const bytes = sizes[type] * itemCount;
      if (!tag || !sizes[type] || !Number.isFinite(bytes) || bytes > 4096) continue;
      const data = bytes <= 4 ? position + 8 : tiff + u32(position + 8);
      if (data < tiff || data + bytes > view.byteLength) continue;
      result.set(tag, { type, count: itemCount, data });
    }
    return result;
  }

  function ascii(entry) {
    if (!entry || entry.type !== 2) return "";
    let text = "";
    for (let index = 0; index < entry.count; index += 1) {
      const value = view.getUint8(entry.data + index);
      if (!value) break;
      text += String.fromCharCode(value);
    }
    return text.trim();
  }

  function pointer(entry) {
    if (!entry || ![3, 4].includes(entry.type) || entry.count !== 1) return null;
    return entry.type === 3 ? u16(entry.data) : u32(entry.data);
  }

  function rationals(entry) {
    if (!entry || entry.type !== 5 || entry.count > 8) return [];
    const values = [];
    for (let index = 0; index < entry.count; index += 1) {
      const numerator = u32(entry.data + index * 8), denominator = u32(entry.data + index * 8 + 4);
      if (numerator === null || !denominator) return [];
      values.push(numerator / denominator);
    }
    return values;
  }

  const root = entries(u32(tiff + 4));
  const exif = entries(pointer(root.get(0x8769)));
  const dateText = ascii(exif.get(0x9003)) || ascii(exif.get(0x9004)) || ascii(root.get(0x0132));
  const gps = entries(pointer(root.get(0x8825)));
  const latitudeParts = rationals(gps.get(0x0002));
  const longitudeParts = rationals(gps.get(0x0004));
  const result = {};
  const takenAt = parseExifDate(dateText);
  if (takenAt) result.takenAt = takenAt;
  if (latitudeParts.length === 3 && longitudeParts.length === 3) {
    const decimal = parts => parts[0] + parts[1] / 60 + parts[2] / 3600;
    const latitude = decimal(latitudeParts) * (ascii(gps.get(0x0001)).toUpperCase() === "S" ? -1 : 1);
    const longitude = decimal(longitudeParts) * (ascii(gps.get(0x0003)).toUpperCase() === "W" ? -1 : 1);
    if (Number.isFinite(latitude) && Number.isFinite(longitude) && Math.abs(latitude) <= 90 && Math.abs(longitude) <= 180) {
      result.latitude = latitude;
      result.longitude = longitude;
    }
  }
  return result;
}

async function extractPhotoMetadata(file) {
  let result = {};
  if (file?.type === "image/jpeg" && typeof file.slice === "function") {
    try {
      result = parseJpegExif(await file.slice(0, 262144).arrayBuffer());
    } catch (_) {
      result = {};
    }
  }
  if (!result.takenAt && Number.isFinite(file?.lastModified) && file.lastModified >= 631152000000) {
    result.takenAt = file.lastModified / 1000;
  }
  return result;
}

if (typeof module !== "undefined") module.exports = { extractPhotoMetadata, parseExifDate, parseJpegExif };
