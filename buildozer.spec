# buildozer.spec
# --------------
# WHY THIS FILE EXISTS:
#   Buildozer is the tool that turns this Python/Kivy project into an Android APK.
#   It reads this file to know the app's name, which Python packages to bundle, and which
#   Android permissions to ask for. Run `buildozer android debug` (on Linux or WSL) to build - or just push to GitHub:
#   .github/workflows/build-apk.yml builds the APK automatically on GitHub's Linux computers.

[app]
# Name shown under the icon on the phone.
title = FridgeChef
# Package name + domain form the unique Android id: org.fridgechef.fridgechef
package.name = fridgechef
package.domain = org.fridgechef
# Where the source code is (this folder) and which file types to include in the APK.
source.dir = .
source.include_exts = py,png,jpg,jpeg,ttf
# Folders that must NOT be packed into the APK: tests, the desktop virtual environment, the web
# server (it runs on a computer, not the phone) and the developer asset tools.
# The assets/ folder (recipe pictures, icons, rounded UI shapes) IS included.
source.exclude_dirs = tests,.venv,bin,.buildozer,server,tools
# App version shown in Android settings.
version = 4.0.0
# Python packages bundled into the APK:
#   pyjnius  - lets Python call Android Java APIs (share sheet, gallery)
#   sqlite3  - the local database (on Android it is only built when listed here)
#   openssl  - HTTPS support, needed to talk to the cloud server (same: only built when listed)
#   certifi  - the list of trusted HTTPS certificate authorities (Android's Python has none)
requirements = python3,kivy==2.3.1,pillow,plyer,pyjnius,sqlite3,openssl,certifi
# The launcher icon on the home screen, and the picture shown while the app starts.
icon.filename = %(source.dir)s/assets/app_icon.png
presplash.filename = %(source.dir)s/assets/app_icon.png
# Background colour around the start-up picture (the app's cream background).
android.presplash_color = #F8F5EF
# Lock the screen to portrait - the layout is designed for a phone held upright.
orientation = portrait
# Don't show the app full-screen (keep the Android status bar with the clock visible).
fullscreen = 0

# Permissions:
#   INTERNET               - the Recipes tab calls the FridgeChef web API
#   POST_NOTIFICATIONS     - "Curd expires today" notifications (Android 13+ asks the user)
#   READ_MEDIA_IMAGES      - pick a recipe photo from the gallery (Android 13+)
#   READ_EXTERNAL_STORAGE  - same, for Android 12 and older
#   WRITE_EXTERNAL_STORAGE - save the share card to the gallery on Android 9 and older only
android.permissions = INTERNET, POST_NOTIFICATIONS, READ_MEDIA_IMAGES, READ_EXTERNAL_STORAGE, (name=android.permission.WRITE_EXTERNAL_STORAGE;maxSdkVersion=28)
# Target a recent Android version (required by the Play Store) and support Android 7.0+.
# api 36 + ndk 29 are the values Buildozer's docs require for python-for-android "develop".
android.api = 36
android.minapi = 24
android.ndk = 29
# CPU type to build for. arm64-v8a = 64-bit ARM, used by practically every phone from ~2017 on.
# (Add ", armeabi-v7a" for very old 32-bit phones - the build then takes about twice as long.)
android.archs = arm64-v8a
# Let users back up / restore the app data with their Google account.
android.allow_backup = True
# Accept the Android SDK licence automatically - the build runs unattended on GitHub's computers.
android.accept_sdk_license = True
# A release build makes an .apk (installable file) instead of the default .aab (Play Store only).
android.release_artifact = apk
# Use python-for-android's "develop" branch: it fixes installing libraries that now ship their own
# Android packages (e.g. charset-normalizer 3.5+), and it is the branch required for the Play Store.
p4a.branch = develop

[buildozer]
# 2 = show detailed build logs (useful when something goes wrong).
log_level = 2
# Warn if buildozer is run as the root user.
warn_on_root = 1
