# Dynamic Movie Poster App (Restored with Debugging + Govee Color Sync)
# ---------------------------------------------------------------
import os
import sys
import tkinter as tk
from PIL import Image, ImageTk
import requests
from io import BytesIO
from datetime import datetime, timedelta
import webbrowser
import json
import threading
import random
from http.server import BaseHTTPRequestHandler, HTTPServer
from urllib.parse import urlparse, parse_qs
import time

# =====================================
# Working directory & cache setup
# =====================================
os.chdir(os.path.dirname(os.path.abspath(__file__)))
if not os.path.exists("cache"):
    os.makedirs("cache")
COLOR_CACHE_PATH = os.path.join("cache", "color_cache.json")

# ---- Debug helpers ----
DEBUG = True

def log(*args):
    if DEBUG:
        print("[DEBUG]", *args)

# =====================================
# Splash Screen (boot-time)
# =====================================
class SplashScreen:
    def __init__(self, root, image_path="splash_theater.png", min_ms=12000, on_close=None):
        self.root = root
        self.min_ms = int(min_ms)
        self.top = tk.Toplevel(root)
        self.on_close = on_close
        # Borderless, centered window (no OS chrome)
        try:
            self.top.overrideredirect(True)
        except Exception:
            pass
        self.top.configure(bg="black")
        try:
            # keep above until we position it; we’ll drop topmost shortly
            self.top.attributes("-topmost", True)
        except Exception:
            pass

        # Load image (native size)
        sw = self.top.winfo_screenwidth()
        sh = self.top.winfo_screenheight()
        self._photo = None
        img_w = img_h = 0
        try:
            p = image_path if os.path.isabs(image_path) else os.path.join(os.path.dirname(os.path.abspath(__file__)), image_path)
            img = Image.open(p)
            # Use native image size (no scaling)
            self._photo = ImageTk.PhotoImage(img)
            img_w, img_h = self._photo.width(), self._photo.height()
            self.img_label = tk.Label(self.top, image=self._photo, bg="black")
            self.img_label.pack(expand=True, padx=20, pady=int(sh * 0.03))
        except Exception as e:
            log("Splash image load failed:", e)
            self.img_label = tk.Label(self.top, text="", bg="black")
            self.img_label.pack(expand=True, padx=20, pady=int(sh * 0.05))

        # Loading row: static word + fixed-width dots so text doesn’t jump
        self.dots = 0
        font_size = max(12, int(sh * 0.025))  # half the previous size
        row = tk.Frame(self.top, bg="black")
        row.pack(pady=int(sh * 0.012))
        self.loading_label = tk.Label(row, text="Loading", font=("Consolas", font_size), fg="#D4AF37", bg="black")
        self.loading_label.pack(side="left")
        self.dots_label = tk.Label(row, text="", font=("Consolas", font_size), fg="#D4AF37", bg="black", width=3, anchor="w")
        self.dots_label.pack(side="left")

        # Position window at the center based on requested size
        self.top.update_idletasks()
        w = max(self.top.winfo_reqwidth(), img_w + 40)
        h = self.top.winfo_reqheight()
        x = (sw - w) // 2
        y = (sh - h) // 2
        try:
            self.top.geometry(f"{w}x{h}+{x}+{y}")
        except Exception:
            pass
        try:
            self.top.lift()
            self.top.focus_force()
            # release topmost after showing so other windows can appear later
            self.top.after(200, lambda: self.top.attributes("-topmost", False))
        except Exception:
            pass

        self._animate_id = None
        self._min_elapsed = False
        self._data_ready = False
        self._animate()
        # Ensure it stays up for at least min_ms
        self.root.after(self.min_ms, self._set_min_elapsed)

    def _animate(self):
        self.dots = (self.dots % 3) + 1
        self.dots_label.config(text="." * self.dots)
        self._animate_id = self.top.after(500, self._animate)

    def _set_min_elapsed(self):
        self._min_elapsed = True
        if self._data_ready:
            self._destroy()

    def done(self):
        """Call when background preload is complete."""
        self._data_ready = True
        if self._min_elapsed:
            self._destroy()

    def _destroy(self):
        try:
            if self._animate_id:
                self.top.after_cancel(self._animate_id)
        except Exception:
            pass
        try:
            self.top.destroy()
        except Exception:
            pass
        # Notify that splash has closed so the main window can claim focus cleanly
        try:
            if callable(self.on_close):
                self.root.after(0, self.on_close)
        except Exception:
            pass

# =====================================
# Simple TV state webhook (for Home Assistant) (for Home Assistant)
# =====================================
# Default: TV is OFF until HA tells us otherwise.
TV_IS_ON = False

# Configure via environment variables:
#   TV_WEBHOOK_PORT  (default 8754)
#   TV_WEBHOOK_BIND  (default "0.0.0.0")
#   TV_WEBHOOK_TOKEN (optional; if set, requests must include ?token=...)
WEBHOOK_PORT = int(os.environ.get("TV_WEBHOOK_PORT", "8754"))
WEBHOOK_BIND = os.environ.get("TV_WEBHOOK_BIND", "0.0.0.0")
WEBHOOK_TOKEN = os.environ.get("TV_WEBHOOK_TOKEN", "")

class TVStateHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        global TV_IS_ON
        try:
            parsed = urlparse(self.path)
            if parsed.path not in ("/state", "/tv/state"):
                self.send_response(404); self.end_headers(); return

            qs = parse_qs(parsed.query or "")
            token_ok = True if not WEBHOOK_TOKEN else (qs.get("token", [None])[0] == WEBHOOK_TOKEN)
            if not token_ok:
                self.send_response(403); self.end_headers(); self.wfile.write(b"Forbidden"); return

            tv = (qs.get("tv", [None])[0] or "").lower()
            if tv not in ("on", "off"):
                self.send_response(400); self.end_headers(); self.wfile.write(b"Use ?tv=on|off&token=..."); return

            TV_IS_ON = (tv == "on")
            log(f"Webhook: TV_IS_ON set to {TV_IS_ON}")
            self.send_response(200); self.end_headers(); self.wfile.write(f"ok:{TV_IS_ON}".encode("utf-8"))
        except Exception as e:
            log("Webhook error:", e)
            try:
                self.send_response(500); self.end_headers()
            except Exception:
                pass

    def log_message(self, format, *args):
        # Silence default HTTPServer logging; we use our own logger
        return

def start_tv_webhook_server():
    try:
        server = HTTPServer((WEBHOOK_BIND, WEBHOOK_PORT), TVStateHandler)
    except Exception as e:
        log("TV webhook bind failed:", e)
        return
    t = threading.Thread(target=server.serve_forever, daemon=True)
    t.start()
    log(f"TV webhook listening on {WEBHOOK_BIND}:{WEBHOOK_PORT} (token={'set' if WEBHOOK_TOKEN else 'not set'})")

# Load/save color cache (poster_path filename -> {r,g,b})
try:
    with open(COLOR_CACHE_PATH, "r", encoding="utf-8") as f:
        COLOR_CACHE = json.load(f)
except Exception:
    COLOR_CACHE = {}

def _save_color_cache():
    try:
        with open(COLOR_CACHE_PATH, "w", encoding="utf-8") as f:
            json.dump(COLOR_CACHE, f)
    except Exception as e:
        log("Color cache save failed:", e)

# =====================================
# TMDb API
# =====================================
API_KEY = "30fecaf583412f4f4d044dd98b22f97f"  # your TMDb API key
BASE_URL = "https://api.themoviedb.org/3"
POSTER_BASE_URL = "https://image.tmdb.org/t/p/original"


def fetch_movies(category="now_playing", page=1):
    url = f"{BASE_URL}/movie/{category}?api_key={API_KEY}&language=en-US&page={page}"
    try:
        resp = requests.get(url, timeout=10)
        if resp.status_code != 200:
            log(f"TMDb {category} page {page} HTTP {resp.status_code}: {resp.text[:200]}")
            return []
        data = resp.json()
    except Exception as e:
        log(f"TMDb {category} page {page} request/json error: {e}")
        return []

    results = data.get("results", [])
    for m in results:
        m["category"] = category
    log(f"Fetched {len(results)} from {category} (page {page})")
    return results


def get_trailer_url(movie_id):
    url = f"{BASE_URL}/movie/{movie_id}/videos?api_key={API_KEY}"
    try:
        resp = requests.get(url, timeout=10)
        if resp.status_code != 200:
            log(f"Trailer HTTP {resp.status_code} for {movie_id}: {resp.text[:200]}")
            return None
        for video in resp.json().get("results", []):
            if video.get("site") == "YouTube" and video.get("type") == "Trailer":
                return f"https://www.youtube.com/embed/{video['key']}?autoplay=1"
    except Exception as e:
        log(f"Trailer fetch error for {movie_id}: {e}")
    return None

# Provider cache
provider_cache = {}

def get_streaming_provider(movie_id, region="US"):
    if movie_id in provider_cache:
        return provider_cache[movie_id]
    url = f"{BASE_URL}/movie/{movie_id}/watch/providers?api_key={API_KEY}"
    try:
        resp = requests.get(url, timeout=10)
        if resp.status_code != 200:
            log(f"Providers HTTP {resp.status_code} for {movie_id}: {resp.text[:200]}")
            provider_cache[movie_id] = None
            return None
        data = resp.json().get("results", {})
        region_data = data.get(region, {})
        flatrate = region_data.get("flatrate")
        provider = flatrate[0].get("provider_name") if flatrate else None
        provider_cache[movie_id] = provider
        return provider
    except Exception as e:
        log(f"Providers error for {movie_id}: {e}")
        provider_cache[movie_id] = None
        return None

# =====================================
# Posters & Colors
# =====================================

def get_poster_image(poster_path):
    """Download and return poster image with caching."""
    cache_path = os.path.join("cache", os.path.basename(poster_path))
    if os.path.exists(cache_path):
        try:
            img = Image.open(cache_path)
            img.load()
            return img
        except Exception as e:
            log(f"Cached image open failed {cache_path}: {e}")
            try:
                os.remove(cache_path)
            except Exception:
                pass

    url = f"{POSTER_BASE_URL}{poster_path}"
    try:
        resp = requests.get(url, timeout=15)
        if resp.status_code != 200:
            log(f"Poster HTTP {resp.status_code} {poster_path}: {resp.text[:200]}")
            return None
        with open(cache_path, "wb") as f:
            f.write(resp.content)
        img = Image.open(BytesIO(resp.content))
        img.load()
        log(f"Cached poster {cache_path} size={img.width}x{img.height}")
        return img
    except Exception as e:
        log(f"Poster download/open failed {poster_path}: {e}")
        return None


def _compute_dominant_color(img):
    """Compute a quick dominant RGB color for the given PIL image.
    - Downscale to speed up.
    - Ignore very dark/very bright pixels to avoid black bars/white borders.
    """
    if img.mode not in ("RGB", "RGBA"):
        img = img.convert("RGBA")
    else:
        img = img.copy()

    img.thumbnail((200, 200), Image.LANCZOS)

    pixels = list(img.getdata())
    rgb_pixels = []
    for p in pixels:
        if len(p) == 4:
            r, g, b, a = p
            if a < 16:
                continue
        else:
            r, g, b = p
        s = r + g + b
        if 30 <= s <= 735:
            rgb_pixels.append((r, g, b))

    if not rgb_pixels:
        rgb_pixels = [p[:3] if isinstance(p, tuple) and len(p) == 4 else p for p in pixels][:1000]

    quantized = img.convert("RGB").quantize(colors=8, method=Image.MEDIANCUT)
    palette = quantized.getpalette()
    color_counts = quantized.getcolors()
    if color_counts and palette:
        idx = max(color_counts, key=lambda x: x[0])[1]
        r = palette[3 * idx]
        g = palette[3 * idx + 1]
        b = palette[3 * idx + 2]
        return {"r": int(r), "g": int(g), "b": int(b)}

    n = len(rgb_pixels)
    r = sum(p[0] for p in rgb_pixels) // max(n, 1)
    g = sum(p[1] for p in rgb_pixels) // max(n, 1)
    b = sum(p[2] for p in rgb_pixels) // max(n, 1)
    return {"r": int(r), "g": int(g), "b": int(b)}


def get_or_compute_dominant_color(poster_path):
    key = os.path.basename(poster_path)
    cached = COLOR_CACHE.get(key)
    if cached and all(k in cached for k in ("r", "g", "b")):
        return cached
    img = get_poster_image(poster_path)
    if img is None:
        return {"r": 0, "g": 0, "b": 0}
    color = _compute_dominant_color(img)
    COLOR_CACHE[key] = color
    _save_color_cache()
    return color

# =====================================
# Order mixing helpers
# =====================================

def interleave_by_category(items):
    """Return a list that mixes categories (now_playing / upcoming / popular)
    to avoid long streaks. Randomly shuffles within each bucket, then interleaves.
    """
    buckets = {}
    for m in items:
        cat = m.get("category", "misc")
        buckets.setdefault(cat, []).append(m)
    for lst in buckets.values():
        random.shuffle(lst)
    out = []
    # pop one at a time from a random non-empty bucket
    while any(buckets.values()):
        nonempty = [k for k, v in buckets.items() if v]
        k = random.choice(nonempty)
        out.append(buckets[k].pop())
    return out

# =====================================
# Govee Cloud API (simple)
# =====================================
GOVEE_API_KEY = os.environ.get("GOVEE_API_KEY", "")
GOVEE_DEVICE = os.environ.get("GOVEE_DEVICE", "")     # e.g. "aa:bb:..."
GOVEE_MODEL  = os.environ.get("GOVEE_MODEL", "")       # e.g. "H6159"
GOVEE_CONTROL_URL = "https://developer-api.govee.com/v1/devices/control"


def set_govee_color(rgb):
    """Set the Govee light color using the Cloud API. Expects rgb dict {r,g,b}."""
    if not (GOVEE_API_KEY and GOVEE_DEVICE and GOVEE_MODEL):
        log("Govee not configured; skipping color set.")
        return

    payload = {
        "device": GOVEE_DEVICE,
        "model": GOVEE_MODEL,
        "cmd": {
            "name": "color",
            "value": {"r": int(rgb["r"]), "g": int(rgb["g"]), "b": int(rgb["b"])}
        }
    }
    headers = {
        "Govee-API-Key": GOVEE_API_KEY,
        "Content-Type": "application/json"
    }
    try:
        # Use PUT (POST will return 405)
        r = requests.put(GOVEE_CONTROL_URL, headers=headers, json=payload, timeout=5)
        if r.status_code != 200:
            log(f"Govee color HTTP {r.status_code}: {r.text[:300]}")
    except Exception as e:
        log("Govee color request failed:", e)

# =====================================
# GUI Application
# =====================================
class MoviePosterApp:
    def toggle_fullscreen(self):
        self.fullscreen = not self.fullscreen
        self.root.attributes("-fullscreen", self.fullscreen)

    def __init__(self, root, movies):
        self.root = root
        self.root.attributes('-fullscreen', True)
        self.root.title("Now Playing & Coming Soon")
        self.movies = movies
        self.index = 0

        self.screen_width = self.root.winfo_screenwidth()
        self.screen_height = self.root.winfo_screenheight()

        self.frame = tk.Frame(root, bg="black")
        self.frame.pack(fill="both", expand=True)

        self.title_font_size = int(self.screen_height * 0.04)
        self.fixed_title_height = int(self.screen_height * 0.10)

        self.title_border = tk.Frame(
            self.frame,
            bg="black",
            height=self.fixed_title_height + int(self.screen_height * 0.06),
            highlightthickness=12,
            highlightbackground="#D4AF37",
            bd=0,
            relief="flat"
        )
        self.title_border.pack(fill="x", expand=False, padx=0, pady=(0, 0))

        self.title_label = tk.Label(
            self.title_border,
            text="",
            font=("Broadway", self.title_font_size),
            fg="#D4AF37",
            bg="black",
            wraplength=int(self.screen_height * 9 / 16),
            justify="center"
        )
        self.title_label.pack(padx=4, pady=4)

        self.canvas = tk.Label(self.frame, bg="black")
        self.canvas.pack(fill="both", expand=True)
        self.canvas.bind("<Button-1>", self.handle_click)

        self.root.configure(bg="black")
        self.root.bind("<Escape>", lambda e: self.root.destroy())
        self.root.bind("<f>", lambda e: self.toggle_fullscreen())
        self.root.bind("<Right>", lambda e: self.skip_to_next())
        self.fullscreen = True

        close_button = tk.Button(
            self.title_border,
            text="✕",
            font=("Arial", 12, "bold"),
            fg="#111111",
            bg="black",
            activebackground="black",
            activeforeground="#111111",
            borderwidth=0,
            highlightthickness=0,
            relief="flat",
            command=self.root.destroy,
            cursor="hand2"
        )
        close_button.place(relx=1.0, y=1, anchor="ne")

        # Claim foreground to avoid taskbar sticking/attention highlight
        self.root.after(50, self._claim_foreground)

        self.root.after(100, self.update_display)
        self.schedule_daily_refresh()
        self.schedule_auto_restart()

    def _claim_foreground(self):
        try:
            self.root.lift()
            self.root.attributes("-topmost", True)
            self.root.focus_force()
            self.root.update_idletasks()
            # Give Windows a moment, then release topmost so dialogs work normally
            self.root.after(300, lambda: self.root.attributes("-topmost", False))
        except Exception:
            pass

    def skip_to_next(self):
        if hasattr(self, 'timer'):
            self.root.after_cancel(self.timer)
        self.update_display()

    def _update_govee_async(self, rgb):
        threading.Thread(target=set_govee_color, args=(rgb,), daemon=True).start()

    def update_display(self):
        if not self.movies:
            log("UI: No movies available (self.movies is empty).")
            self.title_label.config(text="No movies available.")
            return

        movie = self.movies[self.index]
        category = movie.get("category")
        if category == "now_playing":
            label_text = "In Theaters Now"
        elif category == "upcoming":
            label_text = "Coming to Theaters"
        elif category == "popular":
            provider = get_streaming_provider(movie["id"])  # cached after first call
            label_text = f"Now Streaming on {provider}" if provider else "Now Streaming"
        else:
            label_text = ""

        # Fit title font to border
        test_font_size = self.title_font_size
        test_label = tk.Label(self.root, text=label_text, font=("Broadway", test_font_size), wraplength=int(self.screen_height * 9 / 16))
        test_label.place(x=-1000, y=-1000)
        test_label.update_idletasks()
        label_width = test_label.winfo_reqwidth()
        label_height = test_label.winfo_reqheight()
        poster_width = int(self.screen_height * 9 / 16)
        while (label_width > poster_width or label_height > self.fixed_title_height) and test_font_size > 10:
            test_font_size -= 1
            test_label.config(font=("Broadway", test_font_size))
            test_label.update_idletasks()
            label_width = test_label.winfo_reqwidth()
            label_height = test_label.winfo_reqheight()
        test_label.destroy()
        self.title_label.config(text=label_text, font=("Broadway", test_font_size))

        # Prepare poster image
        img = get_poster_image(movie["poster_path"])
        if not img or img.width < 800:  # relaxed threshold for robustness
            log(f"Skipping poster for {movie.get('title','?')} (missing or small: {getattr(img,'width',0)}px)")
            self.index = (self.index + 1) % len(self.movies)
            self.update_display()
            return

        canvas_width = self.canvas.winfo_width()
        canvas_height = self.canvas.winfo_height()
        if canvas_width == 0 or canvas_height == 0:
            self.root.after(100, self.update_display)
            return

        total_height = self.screen_height
        target_width = int(total_height * 9 / 16)

        text_height = self.title_label.winfo_reqheight()
        vertical_padding = self.screen_height * 0.02 * 2
        max_image_height = total_height - text_height - vertical_padding

        img_ratio = img.width / img.height
        new_height = max_image_height
        new_width = int(new_height * img_ratio)

        if new_width > target_width:
            new_width = target_width
            new_height = int(new_width / img_ratio)

        if new_width > 0 and new_height > 0:
            img = img.resize((int(new_width), int(new_height)), Image.LANCZOS)
            self.photo = ImageTk.PhotoImage(img)
            self.canvas.config(image=self.photo)

        # Update Govee immediately (dominant color precomputed at load time when possible)
        rgb = movie.get("dominant_color") or get_or_compute_dominant_color(movie["poster_path"])
        if TV_IS_ON:
            self._update_govee_async(rgb)
        else:
            log("TV off (TV_IS_ON=False); skipping Govee color update.")

        self.index = (self.index + 1) % len(self.movies)
        self.timer = self.root.after(15000, self.update_display)

    def handle_click(self, event):
        width = self.canvas.winfo_width()
        if width == 0:
            return
        left_trigger = int(width * 0.15)
        right_trigger = int(width * 0.85)
        if event.x < left_trigger:
            self.index = (self.index - 2) % len(self.movies)
            if hasattr(self, 'timer'):
                self.root.after_cancel(self.timer)
            self.update_display()
        elif event.x > right_trigger:
            if hasattr(self, 'timer'):
                self.root.after_cancel(self.timer)
            self.update_display()
        else:
            self.open_trailer(event)

    def open_trailer(self, event):
        movie = self.movies[(self.index - 1) % len(self.movies)]
        trailer_url = get_trailer_url(movie["id"])
        if trailer_url:
            webbrowser.open(trailer_url)

    def schedule_auto_restart(self):
        four_hours_ms = 4 * 60 * 60 * 1000
        self.root.after(four_hours_ms, self.restart_app)

    def restart_app(self):
        import subprocess, shutil
    
        try:
            script = os.path.abspath(sys.argv[0])
            exe = sys.executable
    
            # Prefer pythonw.exe on Windows to avoid a console window if available
            exe_dir, exe_name = os.path.split(exe)
            pythonw = os.path.join(exe_dir, "pythonw.exe")
            if exe_name.lower().endswith("python.exe") and os.path.exists(pythonw):
                exe = pythonw
    
            # Rebuild argv: interpreter + script + original args (excluding argv[0])
            args = [exe, script] + sys.argv[1:]
    
            # Ensure we restart in the script directory
            cwd = os.path.dirname(script)
    
            log(f"Restarting via spawn: {args} (cwd={cwd})")
    
            # CREATE_NO_WINDOW = 0x08000000 (keeps things quiet if exe is python.exe)
            creationflags = 0x08000000
    
            subprocess.Popen(
                args,
                cwd=cwd,
                close_fds=True,
                creationflags=creationflags
            )
        except Exception as e:
            log("Spawn restart failed; falling back to os.execl:", e)
            try:
                os.execl(sys.executable, sys.executable, *sys.argv)
            except Exception as e2:
                log("os.execl also failed:", e2)
        finally:
            try:
                self.root.destroy()
            except Exception:
                pass
            # Hard-exit so the old process fully dies and frees any resources/ports
            os._exit(0)


    def schedule_daily_refresh(self):
        now = datetime.now()
        next_refresh = now.replace(hour=3, minute=0, second=0, microsecond=0)
        if now >= next_refresh:
            next_refresh += timedelta(days=1)
        delay_ms = int((next_refresh - now).total_seconds() * 1000)
        self.root.after(delay_ms, self.refresh_movies)

    def refresh_movies(self):
        now_playing = fetch_movies("now_playing")

        coming_soon = []
        for page in range(1, 6):
            batch = fetch_movies("upcoming", page=page)
            filtered = [
                m for m in batch
                if m.get("release_date") and datetime.strptime(m["release_date"], "%Y-%m-%d").date() > datetime.today().date()
            ]
            coming_soon.extend(filtered)
        if len(coming_soon) > 20:
            coming_soon = coming_soon[:20]

        now_streaming = []
        for page in range(1, 6):
            batch = fetch_movies("popular", page=page)
            filtered = [m for m in batch if get_streaming_provider(m["id"]) is not None]
            now_streaming.extend(filtered)
        if len(now_streaming) > 20:
            now_streaming = now_streaming[:20]

        movies = [*now_playing, *coming_soon, *now_streaming]
        log(
            f"Counts before poster filter: now_playing={len(now_playing)}, "
            f"coming_soon={len(coming_soon)}, now_streaming={len(now_streaming)}, total={len(movies)}"
        )
        log("Mixing across categories…")
        movies = [m for m in movies if m.get("poster_path")]
        log(f"With poster_path: {len(movies)}")

        prepped = []
        for m in movies:
            img = get_poster_image(m["poster_path"])  # triggers download/cache
            if not img:
                log(f"No image for {m.get('title','?')} ({m['poster_path']})")
                continue
            if img.width < 800:
                log(f"Skipping small image {img.width}px for {m.get('title','?')}")
                continue
            m["dominant_color"] = get_or_compute_dominant_color(m["poster_path"])  # cached
            prepped.append(m)
        log(f"Prepared movies: {len(prepped)}")
        # Interleave by category for variety
        prepped = interleave_by_category(prepped)
        self.movies = prepped
        self.index = 0
        self.update_display()
        self.schedule_daily_refresh()
        self.schedule_auto_restart()


def prepare_movies():
    """Fetch TMDb lists, cache posters, precompute dominant colors, and return prepared list."""
    now_playing = fetch_movies("now_playing")

    coming_soon = []
    for page in range(1, 6):
        batch = fetch_movies("upcoming", page=page)
        filtered = [
            m for m in batch
            if m.get("release_date") and datetime.strptime(m["release_date"], "%Y-%m-%d").date() > datetime.today().date()
        ]
        coming_soon.extend(filtered)
    if len(coming_soon) > 20:
        coming_soon = coming_soon[:20]

    now_streaming = []
    for page in range(1, 6):
        batch = fetch_movies("popular", page=page)
        filtered = [m for m in batch if get_streaming_provider(m["id"]) is not None]
        now_streaming.extend(filtered)
    if len(now_streaming) > 20:
        now_streaming = now_streaming[:20]

    movies = now_playing + coming_soon + now_streaming
    log(
        f"Startup counts: now_playing={len(now_playing)}, coming_soon={len(coming_soon)}, "
        f"now_streaming={len(now_streaming)}, total={len(movies)}"
    )

    prepared = []
    for m in movies:
        if not m.get("poster_path"):
            continue
        img = get_poster_image(m["poster_path"])  # cache fetch
        if not img or img.width < 1400:
            if img:
                log(f"Startup skip small image {img.width}px for {m.get('title','?')}")
            else:
                log(f"Startup no image for {m.get('title','?')}")
            continue
        m["dominant_color"] = get_or_compute_dominant_color(m["poster_path"])  # cached
        prepared.append(m)
    log(f"Startup prepared movies: {len(prepared)}")
    # Interleave by category for variety at startup
    prepared = interleave_by_category(prepared)
    return prepared


if __name__ == "__main__":
    # Start webhook first
    start_tv_webhook_server()

    # Create Tk early so we can show a splash while we preload
    root = tk.Tk()
    # Hide the main window to avoid a white box before the splash
    try:
        root.withdraw()
    except Exception:
        pass

    # Centered splash for at least 12 seconds with animated dots
    splash = SplashScreen(root, image_path="splash_theater.png", min_ms=12000)

    def _bg_prepare():
        prepared = prepare_movies()

        def _launch_main():
            # Build the main app UI only after the splash is fully closed
            app = MoviePosterApp(root, prepared)
            try:
                root.deiconify()
                root.lift()
                # Force focus/foreground and ensure fullscreen takes over taskbar
                root.attributes("-fullscreen", True)
                root.attributes("-topmost", True)
                root.focus_force()
                root.after(300, lambda: root.attributes("-topmost", False))
            except Exception:
                pass

        def _assign_and_done():
            # When the splash closes (min time reached AND data ready), launch main
            splash.on_close = _launch_main
            splash.done()

        root.after(0, _assign_and_done)

    threading.Thread(target=_bg_prepare, daemon=True).start()

    # Run the event loop (splash first, then main UI after preload + 12s)
    root.mainloop()

