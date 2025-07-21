# -*- coding: utf-8 -*-
"""
Created on Sun Jul 20 19:35:08 2025

@author: swebb
"""

import os
import tkinter as tk
from tkinter import ttk
from PIL import Image, ImageTk
import requests
from io import BytesIO
import webbrowser

API_KEY = "YOUR API KEY"  # Replace this with your actual TMDb API key
BASE_URL = "https://api.themoviedb.org/3"
POSTER_BASE_URL = "https://image.tmdb.org/t/p/original"

# Fetch now playing and upcoming movies
def fetch_movies(category="now_playing"):
    url = f"{BASE_URL}/movie/{category}?api_key={API_KEY}&language=en-US&page=1"
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

        self.title_label = tk.Label(
            self.frame,
            text="",
            font=("Helvetica", int(self.screen_height * 0.045), "bold"),
            fg="#FFD700",
            bg="black"
        )
        self.title_label.pack(pady=(10, 0))

        self.canvas = tk.Label(self.frame, bg="black")
        self.canvas.pack(fill="both", expand=True)

        
        self.root.configure(bg="black")
        self.root.bind("<Escape>", lambda e: self.root.destroy())
        self.root.bind("<f>", lambda e: self.toggle_fullscreen())
        self.fullscreen = True
        self.canvas.bind("<Button-1>", self.open_trailer)

        # Add custom close button
        close_button = tk.Button(self.frame, text="✕", font=("Arial", 12), fg="#444444", bg="black", borderwidth=0, highlightthickness=0, command=self.root.destroy, cursor="hand2", relief="flat")
        close_button.place(relx=0.98, rely=0.02, anchor="ne")

        # Defer initial update until layout is finalized
        self.root.after(100, self.update_display)

    def update_display(self):
        if not self.movies:
            self.title_label.config(text="No movies available.")
            return

        movie = self.movies[self.index]
        category = movie.get("category")
        if category == "now_playing":
            label_text = "In Theaters Now"
        elif category == "upcoming":
            label_text = "Coming to Theaters"
        elif category == "popular":
            label_text = "Streaming Now"
        elif category == "top_rated":
            label_text = "Coming to Streaming"
        else:
            label_text = ""
        self.title_label.config(text=label_text)

        img = get_poster_image(movie["poster_path"])
        if img:
            canvas_width = self.canvas.winfo_width()
            canvas_height = self.canvas.winfo_height()

            if canvas_width == 0 or canvas_height == 0:
                self.root.after(100, self.update_display)
                return

            total_height = self.screen_height
            target_width = int(total_height * 9 / 16)

            text_height = self.title_label.winfo_reqheight()
            max_image_height = total_height - text_height

            img_ratio = img.width / img.height
            new_height = max_image_height
            new_width = int(new_height * img_ratio)

            if new_width > target_width:
                new_width = target_width
                new_height = int(new_width / img_ratio)

            if new_width > 0 and new_height > 0:
                img = img.resize((new_width, new_height), Image.ANTIALIAS)
                self.photo = ImageTk.PhotoImage(img)
                self.canvas.config(image=self.photo)

        self.index = (self.index + 1) % len(self.movies)
        self.root.after(10000, self.update_display)

    def open_trailer(self, event):
        movie = self.movies[(self.index - 1) % len(self.movies)]
        trailer_url = get_trailer_url(movie["id"])
        if trailer_url:
            webbrowser.open(trailer_url)

    
if __name__ == "__main__":
    now_playing = fetch_movies("now_playing")
    coming_soon = fetch_movies("upcoming")
    now_streaming = fetch_movies("popular")
    coming_to_streaming = fetch_movies("top_rated")
    movies = now_playing + coming_soon + now_streaming + coming_to_streaming

    movies = [m for m in movies if m.get("poster_path")]

    root = tk.Tk()
    app = MoviePosterApp(root, movies)
    root.mainloop()
