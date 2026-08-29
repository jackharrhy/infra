import { createReadStream } from "node:fs";
import { readFile, stat } from "node:fs/promises";
import { basename, join } from "node:path";
import { Readable } from "node:stream";

const baseUrl = process.env.RADIO_IMPORT_BASE_URL ?? "http://127.0.0.1:44100";
const roomSlug = process.env.RADIO_IMPORT_ROOM ?? "cozy";
const uploadsPath = process.env.RADIO_IMPORT_UPLOADS ?? "/legacy/uploads";
const statePath = process.env.RADIO_IMPORT_STATE ?? "/legacy/radio-state.json";
const state = JSON.parse(await readFile(statePath, "utf8"));
const socket = await connect();
let initialStatePromise = waitForMessage((message) => message.type === "ROOM_STATE");
socket.send(
  JSON.stringify({ type: "JOIN", clientId: "legacy-import", name: "Legacy import" }),
);
let initialState = await initialStatePromise;

if (initialState.snapshot.tracks.length !== 0) {
  throw new Error("Destination room is not empty; refusing a non-idempotent import");
}

let importedIds = [];
let importedByLegacyId = new Map();
for (let [index, track] of state.tracks.entries()) {
  let filename = basename(new URL(track.url, "http://legacy.invalid").pathname);
  let path = join(uploadsPath, filename);
  let file = await stat(path);
  let mediaType = track.mediaType ?? mediaTypeFor(filename);
  let created = await request(`/api/rooms/${roomSlug}/tracks`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ name: filename, mediaType, sizeBytes: file.size }),
  });
  let trackId = created.track.id;
  let uploaded = await request(`/api/rooms/${roomSlug}/tracks/${trackId}/content`, {
    method: "PUT",
    headers: { "Content-Length": String(file.size), "Content-Type": mediaType },
    body: Readable.toWeb(createReadStream(path)),
    duplex: "half",
  });
  if (uploaded.track.id !== trackId) throw new Error(`Upload identity changed for ${filename}`);

  socket.send(JSON.stringify({ type: "RENAME_TRACK", trackId, title: track.title }));
  importedIds.push(trackId);
  importedByLegacyId.set(track.id, trackId);
  console.log(`[${index + 1}/${state.tracks.length}] ${track.title}`);
}

let volumeUpdated = waitForMessage(
  (message) => message.type === "VOLUME_UPDATED" && message.volume === state.volume,
);
socket.send(JSON.stringify({ type: "REORDER_TRACKS", trackIds: importedIds }));
socket.send(JSON.stringify({ type: "SET_VOLUME", volume: state.volume }));
let currentTrackId = importedByLegacyId.get(state.playback.trackId);
if (currentTrackId) {
  socket.send(
    JSON.stringify({
      type: "PAUSE",
      trackId: currentTrackId,
      trackTimeSeconds: state.playback.trackTimeSeconds,
    }),
  );
}

await volumeUpdated;
socket.close();
console.log(`Imported ${importedIds.length} tracks into room ${roomSlug}`);

async function request(path, init) {
  let response = await fetch(baseUrl + path, init);
  let body = await response.json().catch(() => null);
  if (!response.ok) throw new Error(body?.error ?? `${init.method} ${path} failed`);
  return body;
}

async function connect() {
  let url = new URL(`/ws/${roomSlug}`, baseUrl);
  url.protocol = url.protocol === "https:" ? "wss:" : "ws:";
  let websocket = new WebSocket(url);
  await new Promise((resolve, reject) => {
    websocket.addEventListener("open", resolve, { once: true });
    websocket.addEventListener("error", reject, { once: true });
  });
  return websocket;
}

function waitForMessage(predicate) {
  return new Promise((resolve, reject) => {
    let timeout = setTimeout(() => finish(new Error("Timed out waiting for room state")), 30_000);
    let onMessage = (event) => {
      let message = JSON.parse(event.data);
      if (message.type === "ERROR") return finish(new Error(message.message));
      if (predicate(message)) finish(undefined, message);
    };
    let onClose = () => finish(new Error("Room socket closed during import"));
    let finish = (error, value) => {
      clearTimeout(timeout);
      socket.removeEventListener("message", onMessage);
      socket.removeEventListener("close", onClose);
      error ? reject(error) : resolve(value);
    };
    socket.addEventListener("message", onMessage);
    socket.addEventListener("close", onClose, { once: true });
  });
}

function mediaTypeFor(filename) {
  return filename.endsWith(".webm") ? "video/webm" : "audio/mpeg";
}
