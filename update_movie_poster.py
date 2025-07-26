# -*- coding: utf-8 -*-
"""
Created on Fri Jul 25 20:55:49 2025

@author: swebb
"""

import requests

# GitHub raw URL
GITHUB_URL = "https://raw.githubusercontent.com/webbqed/dynamic_movie_poster/main/dynamic_poster.py"

# Local file path
LOCAL_PATH = "C:/Users/Sean/Desktop/Python Scripts/dynamic_poster.py"

try:
    response = requests.get(GITHUB_URL)
    response.raise_for_status()
    with open(LOCAL_PATH, "w", encoding="utf-8") as f:
        f.write(response.text)
    print("✅ Updated dynamic_poster.py from GitHub!")
except Exception as e:
    print(f"❌ Update failed: {e}")
input("Press Enter to exit...")
