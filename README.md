# Dynamic Movie Poster

A fullscreen, zero-clutter movie-poster slideshow for Windows that pulls data from TMDb, caches posters locally, and (optionally) syncs your Govee LED strip to the poster’s dominant color. It refreshes its catalog nightly and auto-restarts for long‑running stability. Includes a tiny built‑in webhook so Home Assistant can tell the app when your TV is on/off—preventing unwanted light changes while the screen is off.

---

## ✨ Features

* **Fullscreen slideshow (Tkinter)** optimized for a 16:9 display.
* **Sources**: TMDb **Now Playing**, **Upcoming**, and **Popular (streaming)**.
* **Poster caching** to disk for smooth transitions.
* **Dominant color detection** (precomputed) to avoid on‑screen lag.
* **Govee Cloud control** (color updates via PUT) triggered **only when TV is on**.
* **Home Assistant webhook**: app exposes `/state?tv=on|off` to flip a runtime flag.
* **Nightly refresh at 3:00 AM** and **auto‑restart every 4 hours**.
* **Simple debug logging** you can toggle with a flag.

> The app **never** turns your Govee light on by itself; it updates color only when `TV_IS_ON` is `True` (set by your HA automation).

---

## 🧩 Requirements

* **Windows 10/11**
* **Python 3.9+** (recommended 3.10+)
* Python packages:

  ```bash
  pip install pillow requests
  ```
* A **TMDb API key**
* (Optional) A **Govee Developer** API key + your device’s **device** and **model** IDs
* (Optional) Home Assistant, if you want TV on/off gating

---

## 🚀 Quick Start

1. **Get the code**
   Place the script in a folder (e.g., `C:\DynamicMoviePoster`). The app auto‑creates a `cache/` folder beside the script.

2. **Install dependencies**

   ```bash
   py -m pip install --upgrade pip
   py -m pip install pillow requests
   ```

3. **Add your TMDb API key**
   Open the script and set:

   ```python
   API_KEY = "YOUR_TMDB_API_KEY"
   ```

4. **Configure Govee (optional, for light sync)**
   Set these **Windows environment variables** (User or System):

   * `GOVEE_API_KEY` – your Govee Developer API key
   * `GOVEE_DEVICE`  – device identifier (looks like a MAC‑like string)
   * `GOVEE_MODEL`   – model code (e.g., `H6159`)

   **Find your device/model** via curl:

   ```bash
   curl -H "Govee-API-Key: YOUR_API_KEY" https://developer-api.govee.com/v1/devices
   ```

   Look for `device` and `model` fields in the JSON response.

5. **(Recommended) Secure the webhook**
   Optionally set a token the app will require on incoming webhook requests:

   * Create **User env var** `TV_WEBHOOK_TOKEN` with a random value.
   * Keep this same token in Home Assistant (see below).

   You can also change the bind/port with env vars:

   * `TV_WEBHOOK_BIND` (default `0.0.0.0`)
   * `TV_WEBHOOK_PORT` (default `8754`)

6. **Run it**
   From a terminal in the app folder:

   ```bash
   py dynamic_poster.py
   ```

   * **ESC** to quit
   * **F** toggles fullscreen
   * **Right Arrow** skips to next poster
   * **Mouse**: left edge = back, right edge = forward, center = open trailer

7. **Add to Startup (optional)**

   * Create a desktop shortcut to `pythonw.exe` that runs your script.
   * Copy that shortcut into `shell:startup` (Start → Run → `shell:startup`).

---

## 🧠 How It Works (High Level)

* At startup and at 3:00 AM, the app fetches movie lists from TMDb.
* For each movie with a viable poster, it downloads/caches the image (if needed), computes a **dominant color** once, and stores it in `cache/color_cache.json`.
* Every 15 seconds the UI advances to the next poster and, **if `TV_IS_ON` is true**, sends a **Govee color** command in a background thread (non‑blocking).
* The built‑in HTTP server listens for **Home Assistant** to call:

  * `GET /state?tv=on&token=...` → sets `TV_IS_ON = True`
  * `GET /state?tv=off&token=...` → sets `TV_IS_ON = False`

---

## 🏠 Home Assistant Integration

Add two `rest_command`s and call them in your TV automation.

**`secrets.yaml`** (recommended)

```yaml
# Either store whole URLs...
tv_webhook_on_url:  "http://192.168.1.50:8754/state?tv=on&token=YOUR_TOKEN"
tv_webhook_off_url: "http://192.168.1.50:8754/state?tv=off&token=YOUR_TOKEN"
# ...or store just the token
tv_webhook_token: YOUR_TOKEN
```

**`configuration.yaml` (Option A – secrets hold the full URLs)**

```yaml
rest_command:
  tv_webhook_on:
    url: !secret tv_webhook_on_url
    method: GET
  tv_webhook_off:
    url: !secret tv_webhook_off_url
    method: GET
```

**`configuration.yaml` (Option B – template the token)**

```yaml
template:
  - sensor:
      - name: tv_webhook_token
        state: !secret tv_webhook_token

rest_command:
  tv_webhook_on:
    url: "http://192.168.1.50:8754/state?tv=on&token={{ states('sensor.tv_webhook_token') }}"
    method: GET
  tv_webhook_off:
    url: "http://192.168.1.50:8754/state?tv=off&token={{ states('sensor.tv_webhook_token') }}"
    method: GET
```

**Automations:**

* When TV turns **on** → call `rest_command.tv_webhook_on`
* When TV turns **off** → call `rest_command.tv_webhook_off`

**Notes**

* Use your PC’s **IPv4** (e.g., `192.168.1.50`) or a resolvable hostname. Consider a **DHCP reservation** so it doesn’t change.
* Open/allow inbound **TCP 8754** (Private network) in Windows Firewall the first time the server starts.
* If you prefer **IPv6**, wrap addresses in brackets: `http://[2601:...]:8754/state?...`

---

## 🔧 Configuration Reference (env vars)

| Name               | Required               | Default   | What it does                                |
| ------------------ | ---------------------- | --------- | ------------------------------------------- |
| `GOVEE_API_KEY`    | Only if using Govee    | —         | Govee Developer API key                     |
| `GOVEE_DEVICE`     | Only if using Govee    | —         | Device identifier returned by `/v1/devices` |
| `GOVEE_MODEL`      | Only if using Govee    | —         | Device model (e.g., `H6159`)                |
| `TV_WEBHOOK_TOKEN` | Optional (recommended) | —         | Shared secret for HA webhook calls          |
| `TV_WEBHOOK_PORT`  | Optional               | `8754`    | Port for the built‑in webhook               |
| `TV_WEBHOOK_BIND`  | Optional               | `0.0.0.0` | Bind address for webhook (`::` for IPv6)    |

Other tunables (edit the script):

* Slide interval: `self.root.after(15000, self.update_display)`
* Poster width threshold: `img.width < 800`
* Debug flag: `DEBUG = True`

---

## 🖥️ Windows Tips

* **Set environment variables:** Start → search “Environment Variables” → *Edit the system environment variables* → **Environment Variables…** → add under **User variables**.
* **Find your IP:** `ipconfig` → copy the **IPv4 Address** of your active adapter.
* **Make it start with Windows:** place a shortcut to `pythonw.exe` (pointing to your script) in `shell:startup`.

---

## 🧪 Troubleshooting

**App says “No movies available”**

* Verify your `API_KEY` in the script.
* Check console for `[DEBUG]` messages (HTTP status codes). Rate limits or network errors will be printed.
* Lower the poster width threshold from `1500` to `800` (already relaxed in this version).
* Delete the `cache/` folder to force redownload.

**`Govee not configured; skipping color set.`**

* One or more of `GOVEE_API_KEY`, `GOVEE_DEVICE`, `GOVEE_MODEL` missing in the **current process**.
* Restart the terminal/app after adding environment variables.

**Govee 405 Method Not Allowed**

* Control calls must be **PUT** to `/v1/devices/control` (the app already uses PUT).

**Webhook 403 Forbidden**

* Token mismatch. Update `TV_WEBHOOK_TOKEN` or the HA URL.

**Webhook reachable issues**

* Open Windows Firewall for the chosen port.
* Ensure HA and the PC are on the same LAN/subnet.
* Use a DHCP reservation so the IP in your HA URLs stays stable.

**Seeing too many Govee calls**

* Calls only happen when `TV_IS_ON=True`. If you still want fewer calls, increase the slide interval or add color de‑duplication logic.

---

## 🧱 Folder Structure & Cache

```
app_folder/
├─ dynamic_poster.py           # the main script
├─ cache/
│  ├─ <poster images>.jpg
│  └─ color_cache.json         # dominant color cache
└─ (optional) govee.json       # if you add a local config fallback
```

---

## 🙏 Credits & Notes

* Movie metadata and poster images from **TMDb**. This product uses the TMDb API but is not endorsed or certified by TMDb.
* Govee device control via **Govee Developer Cloud API**.

---

## 🗺️ Roadmap / Ideas

* Optional **LAN control** for zero cloud calls
* Color de‑duplication / rate limiting toggles
* On‑screen status for TV state and Govee connectivity
* Config file instead of env vars

---

## 📄 License

Personal/non‑commercial use. Adapt freely for your own setup.

