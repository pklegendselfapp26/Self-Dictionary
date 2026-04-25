[app]
# --- App Details ---
title = Insta Word
package.name = instaword
package.domain = org.yourname

source.dir = .
source.include_exts = py,png,jpg,kv,atlas,json,ttf,wav,mp3

# Tells Buildozer to look for your uploaded logo
icon.filename = %(source.dir)s/icon.png

version = 0.1

# --- Requirements ---
# Includes KivyMD, Plyer (for TTS), and Requests (for the API)
requirements = python3, kivy==2.2.1, kivymd==1.1.1, plyer, pyjnius, pillow, requests, urllib3, certifi, charset-normalizer, idna

# --- Display ---
orientation = portrait
fullscreen = 0

# --- Android Specifics ---
# Dual architecture for Realme P4 Pro (arm64-v8a) and Samsung Galaxy J8 (armeabi-v7a)
android.archs = arm64-v8a, armeabi-v7a
android.allow_backup = True

# Permissions required for API fetching and Text-to-Speech
android.permissions = INTERNET, WAKE_LOCK

# Game Mode Bypass: Forces Android to recognize this as a productivity app
android.meta_data = android.app.app_category=productivity

# API Levels
android.api = 34
android.minapi = 21
android.ndk = 25b
android.ndk_api = 21
android.accept_sdk_license = True

[buildozer]
log_level = 2
warn_on_root = 1

