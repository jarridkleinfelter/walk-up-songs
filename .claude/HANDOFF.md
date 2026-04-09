# Walk-Up Songs — Developer Handoff

This document summarises the full development history of the KML Chargers Walk-Up Songs PWA. It is intended either as a handoff to a new developer or as context to resume a Claude conversation where prior history is lost.

---

## Project Overview

A single-page PWA for a baseball team (KML Chargers) that lets a coach play two-part audio walk-up sequences for each player: an announcer intro clip followed by a music clip. Everything is stored locally in the browser (IndexedDB + Service Worker). No server, no build system, no npm. Three files total: `index.html`, `sw.js`, `manifest.json`.

**Live deployment target:** GitHub Pages (HTTPS required for Service Worker)

---

## Architecture

| Concern | Implementation |
|---|---|
| UI | Single `index.html` with inline `<style>` and `<script>` |
| Player metadata | IndexedDB `walkup_db` → `players` object store (keyPath: `id`) |
| Audio blobs | IndexedDB `walkup_db` → `audio_blobs` object store (out-of-line key) |
| Offline shell | Service Worker (`sw.js`) caches `index.html` and `/` in `walkup-v1` cache |
| ZIP import/export | JSZip 3.10.1 via CDN (`unpkg.com`) |
| Drag-to-reorder | SortableJS 1.15.2 via CDN (`jsdelivr.net`) |
| Audio fade-out | Web Audio API — `AudioContext` → `MediaElementSourceNode` → `GainNode` |

### Player Schema (IndexedDB `players` store)
```json
{
  "id": "uuid-string",
  "number": "23",
  "name": "Player Name",
  "announcerKey": "uuid_announcer_timestamp",
  "musicKey": "uuid_music_timestamp",
  "announcerName": "intro.mp3",
  "musicName": "song.mp3",
  "musicStart": 83,
  "order": 0
}
```
`musicStart` is stored in **seconds** (e.g. `83` = 1:23). Defaults to `0`.

### Audio Blob Keys
Format: `{playerId}_{type}_{Date.now()}` — e.g. `abc123_announcer_1712345678901`

---

## Feature Development History

### Initial State (first commit)
- Basic roster (add/delete players)
- Two audio slots per player: announcer intro + music
- IndexedDB storage for both metadata and audio blobs
- Service Worker for offline support
- Now Playing bar (fixed bottom) with progress bar and Stop button
- Toast notifications

### Feature: Import / Export
- Added **JSZip** via CDN script tag
- `exportData()` — serialises `players` array to `players.json`, fetches all audio blobs from IDB, bundles into a zip, triggers download
- `importData(file)` — reads zip, clears all existing IDB data, restores audio blobs then player records, re-renders
- UI: two `.btn-secondary` outline buttons in an `.io-row` div (later moved into the collapsible manage panel)

### Feature: Edit Player (name / number)
- Added `editingPlayerId` state variable
- `openEdit(id)` / `cancelEdit()` / `saveEdit(id)` functions
- Inline edit form renders inside the player card header when editing, replacing name/number/status with two inputs
- Enter key saves, Escape cancels
- Edit/delete buttons moved to a `.card-footer` row at the bottom of each card (see next item)

### UI: Play Button + Card Footer
- Play button enlarged: `44px` → `60px`, font-size `18px` → `24px`
- Edit (✎ Edit) and Delete (✕ Remove) buttons moved out of the player header into a `.card-footer` row at the bottom of the card — prevents accidental taps when trying to play
- Lightning bolt icons `⚡` in header replaced with softball emoji `🥎`
- "Add Player" card: removed baseball emoji from heading, relabelled `#` field to `Player #`, widened field group to `90px`, moved Add button to its own centered row below the inputs

### Feature: Drag-to-Reorder
- Added **SortableJS** via CDN script tag
- `sortableInstance` module-level variable, destroyed and recreated on each `renderPlayers()` call (because innerHTML is replaced)
- `initSortable()` — creates Sortable on `#player-list` with `handle: '.drag-handle'`
- On drag end: splices `players` array, updates `order` field on all players, persists each to IDB
- Drag handle `⠿` added to left of player card header (non-edit mode only)
- CSS: `.sortable-ghost` (opacity 0.35) and `.sortable-drag` (elevated shadow)
- Skipped when roster has fewer than 2 players

### Feature: Music Start Timestamp
- Added `musicStart` field (seconds, default `0`) to player schema
- `⏱ Start` row renders below the music file button **only when a music file is attached**
- Input accepts `m:ss` format (e.g. `1:23`) or plain seconds
- `formatTime(secs)` — converts seconds to `m:ss` string
- `parseTimestamp(val)` — parses `m:ss` or plain number to seconds
- `saveMusicStart(id, val)` — saves to IDB, normalises display value without full re-render
- Saves on `blur` or Enter key

### Feature: Music Clip (7-second playback)
- `playBlob(key, { startTime, clipDuration })` refactored to accept options
- Announcer: called with defaults (`startTime=0, clipDuration=null`) — plays in full
- Music: called with `{ startTime: p.musicStart || 0, clipDuration: 7 }`
- On `canplaythrough`: seeks to `startTime`, then plays
- `currentClipTimer` (`setTimeout`) stops audio after `clipDuration` seconds
- `stopAll()` updated to clear `currentClipTimer`

### Feature: Fade-Out (last 2 seconds)
**First attempt (broken on iOS):** Used `audio.volume` in the polling interval — works on desktop browsers but **iOS Safari ignores `audio.volume` assignments** (it is read-only on iOS).

**Final implementation (Web Audio API):**
- Module-level `audioCtx` (lazy singleton via `getAudioCtx()`)
- Each `playBlob` call: creates `new Audio(url)`, then `ctx.createMediaElementSource(audio)` → `ctx.createGain()` → `gainNode.connect(ctx.destination)`
- Gain ramp scheduled **after** `await audio.play()` resolves using `ctx.currentTime`:
  - `gainNode.gain.setValueAtTime(1, ctx.currentTime + 5)` — hold full volume for 5s
  - `gainNode.gain.linearRampToValueAtTime(0, ctx.currentTime + 7)` — ramp to 0 over final 2s
- `ctx.resume()` called before `audio.play()` to satisfy iOS user-gesture requirement
- Progress bar interval reduced to `200ms` (no longer needs 50ms since volume is handled by the audio engine)

### Fix: iOS File Picker (grayed-out files)
**Problem:** After the Web Audio changes, the user reported that all files appeared grayed out in the iOS Safari file picker.

**Root cause:** iOS Safari requires `<input type="file">` to be **attached to the DOM** before `.click()` is called. Dynamically created inputs that are never appended cause the picker to open in a restricted state.

**Fix in `pickFile()`:**
1. Input is appended to `document.body` (hidden via `position:fixed; opacity:0; pointer-events:none`) before `.click()`
2. Removed from DOM in the `change` handler after file is selected
3. A `focus` event listener on `window` (with 500ms delay) cleans up the input if the user cancels without picking
4. `accept` attribute changed from `audio/*` to `audio/*,.mp3,.m4a,.aac,.wav,.flac,.ogg,.opus,.mp4` — explicit extensions alongside the MIME type are needed for iOS to match files correctly

### UI: Collapsible Manage Panel
- Add Player card and Import/Export row wrapped in `<div id="manage-panel">` — hidden by default (`max-height: 0; overflow: hidden`)
- `#btn-manage` button added to the header: toggles `.open` class on both panel and button
- CSS `max-height` transition (`0 → 500px`) for smooth slide animation
- Button text toggles between `⚙ Manage Roster` and `✕ Close`
- Rationale: during a game the add/import/export controls are not needed; hiding them keeps the play UI clean

---

## Key Technical Decisions & Gotchas

### iOS Safari Audio
- `audio.volume` is **read-only** on iOS — always use Web Audio `GainNode` for volume control
- `AudioContext` starts `suspended` on iOS until a user gesture — always call `ctx.resume()` before `audio.play()`
- `createMediaElementSource(audio)` can only be called **once per HTMLMediaElement** — a new `Audio()` must be created for each `playBlob` call
- File inputs must be **in the DOM** when `.click()` is called on iOS

### IndexedDB
- `audio_blobs` store uses out-of-line keys (key passed explicitly to `.put()`)
- `players` store uses in-line key (`keyPath: 'id'`)
- All IDB operations are wrapped in promise helpers: `txGet`, `txPut`, `txDelete`, `txGetAll`

### SortableJS + innerHTML
- `renderPlayers()` replaces `#player-list` innerHTML entirely — SortableJS loses its binding
- `initSortable()` is called at the end of every `renderPlayers()`, destroying the previous instance first
- `onEnd` callback uses array splice + IDB writes to persist new order

### Service Worker Cache
- Cache name: `walkup-v1` (in `sw.js`)
- Only caches the app shell (`/` and `/index.html`) — audio blobs live in IndexedDB, not Cache Storage
- If you update the app and need to force clients to get the new version, increment the cache name to `walkup-v2`

### GitHub Pages
- `start_url` in `manifest.json` is currently `/` — if the repo is not at the root of the domain (e.g. `username.github.io/repo-name/`), this must be updated to `/repo-name/`
- iOS home screen icon requires `<link rel="apple-touch-icon">` pointing to a PNG — the manifest icons are **ignored** by iOS Safari. This was noted but not implemented in v1.

---

## Known Limitations / Future Work

- **iOS home screen icon** — needs a `apple-touch-icon` PNG linked in `<head>`. Currently iOS shows a screenshot thumbnail.
- **CDN dependency** — JSZip and SortableJS are loaded from CDN. If CDN is unreachable (and not browser-cached), export/import and drag-to-reorder won't work. Could be inlined for full offline support.
- **No undo for import** — importing immediately overwrites all data after a `confirm()` dialog. Could add a pre-import export as a safety net.
- **Single-origin storage** — IndexedDB is scoped to the origin. Data cannot be shared between Safari and Chrome on the same device, or across devices without export/import.
- **Audio clip duration is hardcoded** — 7 seconds (5s full + 2s fade) is hardcoded in `handlePlay`. Could be made configurable per player.
- **No reorder for imported data** — `order` fields are preserved from the export, so imported rosters maintain their original order.

---

## CSS Colour Tokens

```css
--navy:  #000000   /* page background */
--navy2: #111111   /* card background */
--navy3: #1f1f1f   /* input background */
--gold:  #00703C   /* primary accent (green) */
--gold2: #005a30   /* primary accent dark */
--white: #ffffff
--gray:  #888888   /* muted text */
--gray2: #cccccc   /* secondary text */
```
Note: `--red` and `--red2` are defined but set to the same green values as `--gold` — team colours.

---

## v1 Sign-off

All features working and tested as of 2026-04-09:
- ✅ Add / edit / delete players
- ✅ Attach announcer intro and music files
- ✅ Music start timestamp (m:ss input)
- ✅ 7-second clip with 2-second fade (Web Audio API, works on iOS Safari)
- ✅ Drag-to-reorder roster
- ✅ Now Playing bar with progress
- ✅ Import / Export as .zip
- ✅ Collapsible manage panel
- ✅ iOS file picker fix (DOM-attached input + explicit accept extensions)
- ✅ PWA installable (Service Worker + manifest)
