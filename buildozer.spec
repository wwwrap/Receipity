[app]
title = ReceiptWise
package.name = receiptwise
package.domain = org.receiptwise
source.dir = .
source.include_exts = py,kv,png,jpg,jpeg
source.exclude_dirs = tests,test,.venv,.buildozer,bin,backend,frontend,sampleData,models,data,__pycache__,.test-data
source.exclude_patterns = fetch_samples.py,pre_download_models.py,ocr_demo.py,test_db.py
version = 0.1.0
requirements = python3,kivy==2.3.1,pillow,pyjnius,sqlite3
orientation = portrait
fullscreen = 0
android.api = 35
android.minapi = 23
android.archs = arm64-v8a, x86_64
android.accept_sdk_license = False
android.enable_androidx = True
android.debug_artifact = apk
# ACTION_OPEN_DOCUMENT grants access to the selected image; no broad storage permission.

[buildozer]
log_level = 2
warn_on_root = 1
