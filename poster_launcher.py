import tkinter as tk
from tkinter import ttk
from PIL import Image, ImageTk
import subprocess
import os

# Set these paths to your actual environment and script
PYTHONW_PATH = r"C:\Users\Sean\AppData\Local\spyder-6\envs\spyder-runtime\pythonw.exe"
SCRIPT_PATH = r"C:\Users\Sean\Desktop\random python scripts\dynamic_poster.py"

SPLASH_IMAGE = "splash_theater.png"  # Save the image with this name in the same folder


def launch_app():
    subprocess.Popen([PYTHONW_PATH, SCRIPT_PATH], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    root.destroy()


root = tk.Tk()
root.overrideredirect(True)  # No window decorations
root.configure(bg="black")

# Size and position
width, height = 700, 450
screen_width = root.winfo_screenwidth()
screen_height = root.winfo_screenheight()
x = (screen_width // 2) - (width // 2)
y = (screen_height // 2) - (height // 2)
root.geometry(f"{width}x{height}+{x}+{y}")

# Load splash image
try:
    image = Image.open(SPLASH_IMAGE)
    image = image.resize((600, 340), Image.LANCZOS)
    photo = ImageTk.PhotoImage(image)
    img_label = tk.Label(root, image=photo, bg="black")
    img_label.pack(pady=(20, 10))
except Exception as e:
    tk.Label(root, text="Image failed to load", fg="white", bg="black").pack(pady=20)
    print("Error loading splash image:", e)

# Loading label
label = tk.Label(root, text="Launching Webb's Dynamic Movie Poster...", font=("Broadway", 16), fg="#FFD700", bg="black")
label.pack()

# Progress bar
progress = ttk.Progressbar(root, mode='indeterminate', length=400)
progress.pack(pady=15)
progress.start()

# Launch the app after 3.5 seconds
root.after(3500, launch_app)
root.mainloop()