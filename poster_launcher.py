import tkinter as tk
from PIL import Image, ImageTk
import subprocess
import os
import sys
import time

# Optional: pip install pygetwindow to detect when the app window opens in fullscreen
try:
    import pygetwindow as gw
except ImportError:
    gw = None

# Configuration
MIN_DISPLAY_TIME = 15.0  # minimum splash display time in seconds
ANIMATION_INTERVAL = 500  # milliseconds between animation frames

# Determine script directory and interpreter
script_dir = os.path.dirname(os.path.abspath(__file__))
python_executable = sys.executable  # Use the same interpreter running this script

# Paths relative to this script's folder
SCRIPT_PATH = os.path.join(script_dir, "dynamic_poster.py")
SPLASH_IMAGE = os.path.join(script_dir, "splash_theater.png")

# Create the splash window with a dot-loading animation
def create_splash():
    root = tk.Tk()
    root.overrideredirect(True)
    root.configure(bg="black")

    # Center splash
    width, height = 700, 450
    sw, sh = root.winfo_screenwidth(), root.winfo_screenheight()
    x = (sw // 2) - (width // 2)
    y = (sh // 2) - (height // 2)
    root.geometry(f"{width}x{height}+{x}+{y}")
    root.update()

    # Load splash image
    try:
        img = Image.open(SPLASH_IMAGE)
        img = img.resize((600, 340), Image.LANCZOS)
        photo = ImageTk.PhotoImage(img, master=root)
        lbl = tk.Label(root, image=photo, bg="black")
        lbl.photo = photo
        lbl.pack(pady=(20, 10))
    except Exception as e:
        tk.Label(root, text="Image failed to load", fg="white", bg="black").pack(pady=20)
        print("Error loading splash image:", e)

    # Status label
    tk.Label(root, text="Launching Webb's Dynamic Movie Poster", font=("Broadway", 16), fg="#FFD700", bg="black").pack()

    # Dot animation label
    anim_label = tk.Label(root, text="", font=("Broadway", 16), fg="#FFD700", bg="black")
    anim_label.pack(pady=15)
    anim_label.frames = ["", ".", "..", "...", "...."]
    anim_label.idx = 0

    def animate():
        anim_label.config(text=anim_label.frames[anim_label.idx])
        anim_label.idx = (anim_label.idx + 1) % len(anim_label.frames)
        root.after(ANIMATION_INTERVAL, animate)

    animate()  # start animation
    root.start_time = time.time()
    return root

# Launch the poster app
def launch_app(root):
    # Ensure splash shows at least the minimum time
    def close_splash():
        root.destroy()

    # Verify script exists
    if not os.path.isfile(SCRIPT_PATH):
        print(f"Script not found: {SCRIPT_PATH}")
        close_splash()
        return

    # Start the poster script
    subprocess.Popen(
        [python_executable, SCRIPT_PATH],
        cwd=script_dir,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL
    )

    # Poll for fullscreen window or fallback after minimum time
    if gw:
        def check_window():
            sw, sh = root.winfo_screenwidth(), root.winfo_screenheight()
            for w in gw.getAllWindows():
                if w.title == "Webb's Dynamic Movie Poster" and w.width == sw and w.height == sh:
                    elapsed = time.time() - root.start_time
                    wait = max(0, MIN_DISPLAY_TIME - elapsed)
                    root.after(int(wait * 1000), close_splash)
                    return
            root.after(100, check_window)
        root.after(100, check_window)
    else:
        elapsed = time.time() - root.start_time
        delay = int(max(0, MIN_DISPLAY_TIME - elapsed) * 1000)
        root.after(delay, close_splash)

# Main
if __name__ == '__main__':
    splash = create_splash()
    launch_app(splash)
    splash.mainloop()
