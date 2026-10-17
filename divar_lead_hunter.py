import os
import time
import random
import sqlite3
import requests

# ==================== دریافت تنظیمات از متغیرهای محیطی ====================
RUBIKA_BOT_TOKEN = os.environ.get("RUBIKA_BOT_TOKEN", "").strip()
RUBIKA_CHAT_ID = os.environ.get("RUBIKA_CHAT_ID", "").strip()

if not RUBIKA_BOT_TOKEN or not RUBIKA_CHAT_ID:
    print("[!] هشدار: مقادیر RUBIKA_BOT_TOKEN یا RUBIKA_CHAT_ID در Environment Variables تنظیم نشده‌اند.")

RUBIKA_API_URL = f"https://messengerg2c42.iranlms.ir/v3/{RUBIKA_BOT_TOKEN}/sendMessage"

# کدهای شهرهای هدف در دیوار: "1" = تهران، "5" = کرج
CITY_IDS = ["1", "5"]

# ==================== کلیدواژه‌های هدف (B2B و B2C خریداران) ====================
KEYWORDS = [
    # ۱. خریداران مستقیم خانگی
    "خریدار مبل",
    "خریدار کاناپه",
    "خریدار مبل تخت",
    "خریدار صندلی",
    "خریدار پاف",
    "نیازمند مبل",
    "نیازمند صندلی",
    "نیازمند تخت",
    "تخت خواب شو",
    "مبل کمجا",
    "مبل شو",

    # ۲. پروژه‌های کافه و رستوران (مشتریان صندلی فلزی، تدی و کانتر)
    "تجهیز کافه",
    "تجهیز رستوران",
    "تجهیز کافی شاپ",
    "صندلی کافه",
    "صندلی رستورانی",
    "صندلی اپنی",
    "صندلی بار",
    "صندلی کانتر",
    "میز و صندلی کافه",
    "واگذاری کافه",
    "واگذاری کافی شاپ",
    "صندلی پایه فلزی",

    # ۳. سالن‌های زیبایی، مزون‌ها و کلینیک‌ها (مشتریان پاف و صندلی تدی)
    "تجهیز سالن زیبایی",
    "تجهیز سالن",
    "تجهیز آرایشگاه",
    "تجهیز مزون",
    "تجهیز کلینیک",
    "صندلی لاین ناخن",
    "صندلی انتظار",
    "پاف انتظار",
    "پاف مزون",
    "پاف گرد",
    "صندلی تدی",
    "واگذاری سالن زیبایی",
    "واگذاری لاین",

    # ۴. هوم‌آفیس، سوئیت‌ها، اقامتگاه‌ها و خوابگاه‌ها (مشتریان تخت فومی و بین‌بگ)
    "تجهیز هوم آفیس",
    "تجهیز دفتر کار",
    "تجهیز سوئیت",
    "تجهیز اقامتگاه",
    "تجهیز بومگردی",
    "تجهیز ویلا",
    "تجهیز خوابگاه",
    "تخت تاشو",
    "تخت یک نفره کمجا",
    "تخت خواب فومی",
    "بین بگ",
    "مبل شنی",

    # ۵. پروژه‌های دکوراسیون و تجهیز
    "سفارش مبلمان پروژه",
    "تامین مبلمان",
    "دکوراسیون داخلی اداری",
    "چیدمان کافه",
    "چیدمان سالن"
]

# ==================== بلک‌لیست (حذف کارگاه‌های رقیب، دلال‌ها و سمساری‌ها) ====================
BLACKLIST = [
    "تولیدی", "تولید کننده", "کارخانه", "کارگاه", "پخش عمده", "ارسال از کارخانه", 
    "پخش مستقیم", "صنایع چوب", "کلاف خام", "کلاف چوب", "فروش عمده",
    "چهاردانگه", "یافت آباد", "نعمت آباد", "مرتضی گرد", "دلاوران", "حسن آباد", "خلازیر",
    "اقساطی", "بدون پیش پرداخت", "چک صیادی", "دم قسط", "بدون بهره",
    "تعمیرات مبل", "تعویض رویه", "رویه کوبی", "تعمیر صندلی", "ضایعات فوم", "ضایعات اسفنج"
]

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
    "Content-Type": "application/json",
    "Accept": "application/json"
}

# ==================== مدیریت پایگاه داده SQLite ====================
def init_db():
    conn = sqlite3.connect("divar_leads.db")
    c = conn.cursor()
    c.execute('''
        CREATE TABLE IF NOT EXISTS seen_posts (
            token TEXT PRIMARY KEY,
            title TEXT,
            district TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    conn.commit()
    conn.close()

def is_seen(token):
    conn = sqlite3.connect("divar_leads.db")
    c = conn.cursor()
    c.execute("SELECT token FROM seen_posts WHERE token = ?", (token,))
    row = c.fetchone()
    conn.close()
    return row is not None

def mark_as_seen(token, title, district):
    conn = sqlite3.connect("divar_leads.db")
    c = conn.cursor()
    try:
        c.execute(
            "INSERT INTO seen_posts (token, title, district) VALUES (?, ?, ?)",
            (token, title, district)
        )
        conn.commit()
    except sqlite3.IntegrityError:
        pass
    conn.close()

# ==================== ارسال آلارم به بات روبیکا ====================
def send_rubika_alert(title, district, token, matched_kw):
    post_url = f"https://divar.ir/v/{token}"
    msg = (
        f"🎯 **لید هدف جدید در دیوار کشف شد!**\n\n"
        f"🏷 **کلمه کلیدی:** {matched_kw}\n"
        f"📌 **عنوان آگهی:** {title}\n"
        f"📍 **منطقه:** {district}\n\n"
        f"🔗 **لینک مشاهده و تماس فوری:**\n{post_url}"
    )

    payload = {
        "chat_id": RUBIKA_CHAT_ID,
        "text": msg
    }

    try:
        res = requests.post(RUBIKA_API_URL, json=payload, timeout=10)
        if res.status_code == 200:
            print(f"[+] پیام روبیکا با موفقیت ارسال شد: {title}")
        else:
            print(f"[-] روبیکا خطا داد (Status {res.status_code}): {res.text}")
    except Exception as e:
        print(f"[-] خطای اتصال به روبیکا: {e}")

# ==================== اسکنر دیوار ====================
def scan_divar(keyword):
    search_url = "https://api.divar.ir/v8/postlist/w/search"
    payload = {
        "city_ids": CITY_IDS,
        "search_data": {
            "query": keyword
        }
    }

    try:
        res = requests.post(search_url, headers=HEADERS, json=payload, timeout=12)
        if res.status_code != 200:
            print(f"[-] دیوار پاسخ نداد. کد وضعیت: {res.status_code}")
            return

        data = res.json()
        posts = data.get("widget_list", [])

        for item in posts:
            post_data = item.get("data", {})
            token = post_data.get("token")
            title = post_data.get("title", "")
            district = post_data.get("district", "نامشخص")

            if not token or is_seen(token):
                continue

            # فیلتر آگهی‌های رقیب، کارگاه‌ها و آگهی‌های اسپم
            if any(bad_word in title for bad_word in BLACKLIST):
                mark_as_seen(token, title, district)
                continue

            # ثبت آگهی و ارسال نوتیفیکیشن
            print(f"[+] لید منطبق پیدا شد: {title} ({district})")
            mark_as_seen(token, title, district)
            send_rubika_alert(title, district, token, keyword)

    except Exception as ex:
        print(f"[-] خطای ارتباطی در اسکن دیوار: {ex}")

# ==================== حلقه اجرای دائم ====================
if __name__ == "__main__":
    init_db()
    print("=" * 60)
    print("🚀 مانیتورینگ خودکار دیوار + اطلاع‌رسانی روبیکا فعال شد...")
    print(f"📍 شهرهای هدف: {CITY_IDS} (تهران و کرج)")
    print(f"🔍 تعداد کلیدواژه‌ها: {len(KEYWORDS)} مورد")
    print("=" * 60)

    while True:
        for kw in KEYWORDS:
            scan_divar(kw)
            # تاخیر تصادفی بین ۲ تا ۴ ثانیه برای طبیعی بودن درخواست‌ها
            time.sleep(random.uniform(2.2, 4.2))

        print("[*] یک دور اسکن تمام شد. استراحت سیستم به مدت ۱۸۰ ثانیه...")
        time.sleep(180)
