import os
import time
import random
import sqlite3
import requests

# خواندن متغیرها از تنظیمات Render (امن و استاندارد)
RUBIKA_BOT_TOKEN = os.environ.get("RUBIKA_BOT_TOKEN", "YOUR_DEFAULT_TOKEN")
RUBIKA_CHAT_ID = os.environ.get("RUBIKA_CHAT_ID", "YOUR_DEFAULT_CHAT_ID")
RUBIKA_API_URL = f"https://messengerg2c42.iranlms.ir/v3/{RUBIKA_BOT_TOKEN}/sendMessage"

# بقیه بخش‌های کد و کلمات کلیدی بدون تغییر باقی می‌مانند...
