[app]
# -- General Info --
title = My Dictionary App
package.name = mydictapp
package.domain = org.yourname

source.dir = .
# Added 'ttf' and 'wav'/'mp3' just in case you add custom fonts or sounds later!
source.include_exts = py,png,jpg,kv,atlas,json,ttf,wav,mp3

version = 0.1

# -- Requirements --
# Included plyer for TTS, and pyjnius to talk to Android.
requirements = python3, kivy==2.2.1, kivymd==1.1.1, plyer, pyjnius, pillow, certifi, urllib3, charset-normalizer, idna

# -- Display --
orientation = portrait
fullscreen = 0

# -- Android Specifics --
# Both architectures: armeabi-v7a (for Samsung J8) and arm64-v8a (for Realme)
android.archs = arm64-v8a, armeabi-v7a
android.allow_backup = True

# Permissions required for Text-to-Speech to work properly
android.permissions = INTERNET, WAKE_LOCK

# Fix for Realme GT Boost / Game Mode
android.meta_data = android.app.app_category=productivity

# API Settings
android.api = 34
android.minapi = 21
android.ndk = 25b
android.ndk_api = 21
android.accept_sdk_license = True

[buildozer]
log_level = 2
warn_on_root = 1
