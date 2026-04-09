# KML Chargers – Walk-Up Songs

A mobile-first Progressive Web App (PWA) for managing and playing baseball walk-up song sequences. Built for the KML Chargers, it lets a coach or scorekeeper assign two-part audio clips to each player — an announcer intro followed by a walk-up song — and play them with a single tap.

---

## Features

- **Roster management** — Add, edit, and remove players with jersey number and name
- **Two-part audio per player** — An announcer intro clip (plays in full) followed by a music clip
- **Music start timestamp** — Set the exact point in the song to start from (e.g. `1:23`), plays for 7 seconds
- **Fade-out** — Music fades smoothly over the final 2 seconds of the 7-second clip
- **Drag-to-reorder** — Long-press and drag the ⠿ handle to reorder the roster
- **Now Playing bar** — Fixed bottom bar shows the current player name, phase, and a progress bar
- **Import / Export** — Back up the entire roster and all audio files as a `.zip`, and restore from that zip on any device
- **Offline support** — Works fully offline once loaded (Service Worker + IndexedDB)
- **PWA installable** — Can be saved to the iPhone home screen for a full-screen native-like experience

---

## How It Works

### Data Storage
All data is stored entirely in the browser — there is no server or backend.

- **Player metadata** (name, number, audio file names, start timestamp, order) is stored in **IndexedDB** (`walkup_db`, `players` store)
- **Audio blobs** (the actual audio files) are stored in **IndexedDB** (`walkup_db`, `audio_blobs` store), keyed by `{playerId}_{type}_{timestamp}`
- **App shell** (`index.html`) is cached by the **Service Worker** (`walkup-v1` cache) for offline use

### Playback Flow
1. Tap the green ▶ button on a player card
2. The announcer intro plays in full
3. The music clip starts at the saved timestamp and plays for **5 seconds at full volume**, then **fades out over 2 seconds**
4. Playback ends automatically — or tap ■ Stop at any time

Audio playback uses the **Web Audio API** (`AudioContext` → `MediaElementSourceNode` → `GainNode`) to enable gain scheduling. This is required because iOS Safari ignores `audio.volume` assignments — the GainNode approach works cross-platform.

### Import / Export
- **Export** — Serialises all player records to `players.json` and bundles all audio blobs into an `audio/` folder, then downloads as `walkup-songs-YYYY-MM-DD.zip` (uses JSZip)
- **Import** — Reads a previously exported zip, clears existing data, and restores everything. Useful for moving the roster to a new device or browser

---

## File Structure

```
index.html      — Entire application (HTML + CSS + JS, single file)
sw.js           — Service Worker (offline caching)
manifest.json   — PWA web app manifest
README.md       — This file
```

No build system, no npm, no dependencies to install. Everything runs directly in the browser.

### External CDN Dependencies (loaded at runtime)
- **JSZip 3.10.1** — `https://unpkg.com/jszip@3.10.1/dist/jszip.min.js`
- **SortableJS 1.15.2** — `https://cdn.jsdelivr.net/npm/sortablejs@1.15.2/Sortable.min.js`

These are loaded from CDN on each page load. The app requires an internet connection on first load to fetch them; subsequent loads may work offline if the browser has cached them.

---

## Hosting on GitHub Pages

1. Push the repository to GitHub (the three files: `index.html`, `sw.js`, `manifest.json`)
2. Go to **Settings → Pages** in your repository
3. Under **Source**, select `Deploy from a branch` → `main` → `/ (root)`
4. Click **Save** — GitHub will provide a URL like `https://yourusername.github.io/walk-up-songs/`

> **Important:** The Service Worker requires HTTPS. GitHub Pages provides this automatically. The app will **not** work correctly served over plain `http://` (Service Worker will be blocked).

> If you rename the repo, update the `"start_url"` in `manifest.json` to match the new base path, e.g. `"/walk-up-songs/"`.

---

## Saving to iPhone Home Screen (PWA Install)

1. Open the app URL in **Safari** on iPhone (must be Safari — Chrome/Firefox on iOS cannot install PWAs)
2. Tap the **Share** button (the box with an arrow pointing up) in the Safari toolbar
3. Scroll down and tap **"Add to Home Screen"**
4. Edit the name if desired, then tap **Add**

The app will appear on your home screen with a full-screen launch experience (no browser chrome). It will work offline after the first load.

> **Note:** Each browser/device has its own isolated IndexedDB. Data saved in Safari on your iPhone is separate from data in Chrome on your PC. Use **Export Backup** and **Import Backup** to transfer data between devices.

---

## Usage Tips

### Adding Players
Tap **⚙ Manage Roster** in the header to reveal the Add Player form and Import/Export buttons. This panel is hidden by default to keep the play screen clean during a game.

### Setting a Music Start Time
Once a music file is attached to a player, a **⏱ Start** row appears below it. Enter the timestamp in `m:ss` format (e.g. `1:23` for 1 minute 23 seconds) where you want the clip to begin. The app will play 7 seconds from that point (5s full volume + 2s fade).

### Reordering the Roster
Grab the **⠿** handle on the left side of any player card and drag it to reorder. Order is persisted automatically.

### Backing Up Data
Use **⬇ Export Backup** to download a `.zip` of all players and audio files. Store this somewhere safe — it is the only way to move data to another device or recover from clearing browser storage.
