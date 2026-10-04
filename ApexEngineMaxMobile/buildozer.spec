[app]
title = ApexEngine Max
package.name = apexenginemax
package.domain = org.apexengine
source.dir = .
source.include_exts = py,png,jpg,kv,atlas,json,txt,md,conf,java
source.exclude_dirs = .git,__pycache__,bin,dist,build,tests

# Bundle the Java VpnService
android.add_src = src

version = 3.0.0
requirements = python3==3.11.5,kivy==2.3.0,pyjnius,android,plyer
orientation = portrait
fullscreen = 0
icon.filename = %(source.dir)s/icon.png
presplash.filename = %(source.dir)s/presplash.png

[app:android]
android.api = 33
android.minapi = 24
android.ndk = 25b
android.archs = arm64-v8a, armeabi-v7a
android.permissions = INTERNET,ACCESS_NETWORK_STATE,FOREGROUND_SERVICE,POST_NOTIFICATIONS,ACCESS_NOTIFICATION_POLICY,WRITE_SETTINGS,READ_EXTERNAL_STORAGE,WRITE_EXTERNAL_STORAGE,MANAGE_EXTERNAL_STORAGE,KILL_BACKGROUND_PROCESSES,PACKAGE_USAGE_STATS,QUERY_ALL_PACKAGES,RECEIVE_BOOT_COMPLETED,WAKE_LOCK,ACCESS_WIFI_STATE,CHANGE_WIFI_STATE,BIND_VPN_SERVICE
android.services = ApexVpnService:org.apexengine.max.ApexVpnService:exported=true:permission=android.permission.BIND_VPN_SERVICE
android.allow_backup = True
android.release_artifact = apk
android.accept_sdk_license = True

[buildozer]
log_level = 2
warn_on_root = 1
