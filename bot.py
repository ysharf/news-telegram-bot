import os
import json
import time
import requests
import feedparser
from deep_translator import GoogleTranslator

# تحديد مسار ملف الحالة
STATE_FILE = "state.json"

# استدعاء رموز التوثيق من متغيرات البيئة
BOT_TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN")
CHAT_ID = os.environ.get("TELEGRAM_CHAT_ID")

# المصادر (7 مصادر رئيسية)
FEEDS_DATABASE = {
    "💻 تقنية - TechCrunch": "https://techcrunch.com/feed",
    "💻 تقنية - The Verge": "https://www.theverge.com/rss/index.xml",
    "🛡️ سيبراني - The Hacker News": "https://feeds.feedburner.com/TheHackersNews",
    "🛡️ سيبراني - BleepingComputer": "https://www.bleepingcomputer.com/feed/",
    "🌍 عالمي - Reuters": "https://news.google.com/rss/search?q=site:reuters.com&hl=en-US",
    "🌍 إقليمي - BBC Arabic": "https://feeds.bbci.co.uk/arabic/rss.xml",
    "🌍 إقليمي - Al Jazeera Arabic": "https://www.aljazeera.net/aljazeerarss/all.xml"
}

def load_sent_state():
    if os.path.exists(STATE_FILE):
        try:
            with open(STATE_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            return {"sent_urls": []}
    return {"sent_urls": []}

def save_sent_state(state_data):
    with open(STATE_FILE, "w", encoding="utf-8") as f:
        json.dump(state_data, f, ensure_ascii=False, indent=4)

def translate_to_arabic(text):
    if not text or text.strip() == "":
        return ""
    try:
        if any(ord(char) > 1200 for char in text[:15]):
            return text
        translated = GoogleTranslator(source="auto", target="ar").translate(text)
        return translated
    except Exception as e:
        print(f"خطأ في الترجمة: {e}")
        return text

def publish_to_telegram(message):
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
    payload = {
        "chat_id": CHAT_ID,
        "text": message,
        "parse_mode": "HTML",
        "disable_web_page_preview": False
    }
    try:
        response = requests.post(url, json=payload, timeout=12)
        if response.status_code == 200:
            return True
        print(f"فشل الإرسال: {response.text}")
        return False
    except Exception as e:
        print(f"خطأ في الاتصال: {e}")
        return False

def run_pipeline():
    state = load_sent_state()
    sent_urls = set(state.get("sent_urls", []))
    newly_sent = []

    print("بدء جلب الأخبار من 7 مصادر...")

    for category, feed_url in FEEDS_DATABASE.items():
        try:
            headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"}
            r = requests.get(feed_url, headers=headers, timeout=10)
            parsed_feed = feedparser.parse(r.content)
        except Exception as e:
            print(f"تخطي {category}: {e}")
            continue

        for entry in parsed_feed.entries[:1]:  # خبر واحد فقط من كل مصدر
            link = entry.get("link")
            title = entry.get("title")

            if not link or link in sent_urls:
                continue

            print(f"خبر جديد في {category}: {title}")

            translated_title = translate_to_arabic(title)
            summary = entry.get("summary", "")
            if summary and len(summary) > 250:
                summary = summary[:250] + "..."
            translated_summary = translate_to_arabic(summary) if summary else ""

            telegram_msg = (
                f"<b>{category}</b>\n\n"
                f"📌 <b>العنوان:</b> {translated_title}\n\n"
            )
            if translated_summary:
                clean_summary = translated_summary.replace("<", "&lt;").replace(">", "&gt;")
                telegram_msg += f"📝 <b>التفاصيل:</b> {clean_summary}\n\n"
            
            telegram_msg += f"🔗 <b>الرابط الأصلي:</b> <a href='{link}'>اضغط هنا للمتابعة</a>"

            if publish_to_telegram(telegram_msg):
                sent_urls.add(link)
                newly_sent.append(link)
                time.sleep(2)

    if newly_sent:
        state["sent_urls"] = list(sent_urls)[-1500:]
        save_sent_state(state)
        print("تم تحديث سجل الحالة بنجاح.")
    else:
        print("لا توجد أخبار جديدة.")

if __name__ == "__main__":
    if not BOT_TOKEN or not CHAT_ID:
        print("خطأ: متغيرات البيئة غير موجودة!")
    else:
        run_pipeline()
