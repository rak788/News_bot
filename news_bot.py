import feedparser
import requests
import re
import time
import os
import google.generativeai as genai
from datetime import datetime

# ===================== إعدادات =====================

BOT_TOKEN     = os.environ.get(“BOT_TOKEN”, “”)
CHAT_ID       = os.environ.get(“CHAT_ID”, “”)
GEMINI_API_KEY = os.environ.get(“GEMINI_API_KEY”, “”)

genai.configure(api_key=GEMINI_API_KEY)
model = genai.GenerativeModel(“gemini-1.5-flash”)

# ===================== مصادر RSS الموثوقة =====================

RSS_FEEDS = {
“💰 مال وأسواق”: [
“https://feeds.reuters.com/reuters/businessNews”,
“https://feeds.reuters.com/reuters/companyNews”,
“https://www.cnbc.com/id/10000664/device/rss/rss.html”,
“https://www.cnbc.com/id/15839069/device/rss/rss.html”,
],
“🏢 أعمال ونتائج شركات”: [
“https://feeds.reuters.com/reuters/topNews”,
“https://feeds.ft.com/rss/home/uk”,
“https://www.cnbc.com/id/10001147/device/rss/rss.html”,
],
“🤖 ذكاء اصطناعي”: [
“https://techcrunch.com/category/artificial-intelligence/feed/”,
“https://venturebeat.com/category/ai/feed/”,
“https://www.technologyreview.com/feed/”,
],
“📱 تقنية”: [
“https://www.theverge.com/rss/index.xml”,
“https://feeds.arstechnica.com/arstechnica/technology-lab”,
“https://www.wired.com/feed/rss”,
],
“🌍 أخبار عربية”: [
“https://www.aljazeera.net/xmlfeeds/rss2.0.xml?section=business”,
“https://arabic.rt.com/rss/economy/”,
],
}

# ===================== هاشتاقات =====================

HASHTAGS = {
“💰 مال وأسواق”:          “#أسواق_المال #اقتصاد #استثمار #بورصة”,
“🏢 أعمال ونتائج شركات”:  “#أعمال #شركات #نتائج_مالية #اقتصاد”,
“🤖 ذكاء اصطناعي”:        “#ذكاء_اصطناعي #AI #تقنية #مستقبل”,
“📱 تقنية”:                “#تقنية #تكنولوجيا #ابتكار #عالم_التقنية”,
“🌍 أخبار عربية”:          “#اقتصاد #أعمال #عالم_عربي #أخبار”,
}

# ===================== جلب الأخبار =====================

def fetch_news(feed_url, max_items=3):
try:
feed = feedparser.parse(feed_url)
items = []
for entry in feed.entries[:max_items]:
title   = entry.get(“title”, “”).strip()
summary = entry.get(“summary”, entry.get(“description”, “”)).strip()
link    = entry.get(“link”, “”).strip()
summary = re.sub(r’<[^>]+>’, ‘’, summary)[:300].strip()
if title and link:
items.append({“title”: title, “summary”: summary, “link”: link})
return items
except Exception as e:
print(f”⚠️ خطأ RSS ({feed_url}): {e}”)
return []

# ===================== صياغة بالعربي عبر Gemini =====================

def rewrite_arabic(category, title, summary):
prompt = f”””
أنت محرر أخبار محترف متخصص في {category}.
لديك هذا الخبر:
العنوان: {title}
الملخص: {summary}

المطلوب:

1. اكتب العنوان بالعربي بأسلوب صحفي جذاب (سطر واحد فقط)
1. اكتب ملخص الخبر بالعربي بأسلوب واضح ومختصر (3 أسطر كحد أقصى)

الشروط:

- لغة عربية فصحى مبسطة
- لا تضيف هاشتاقات
- لا تضيف رأيك أو تعليقك
- ابدأ مباشرة بالعنوان بدون مقدمات

الصيغة المطلوبة:
TITLE: [العنوان بالعربي]
BODY: [الملخص بالعربي]
“””
try:
response = model.generate_content(prompt)
text = response.text.strip()
title_ar = “”
body_ar  = “”
for line in text.splitlines():
if line.startswith(“TITLE:”):
title_ar = line.replace(“TITLE:”, “”).strip()
elif line.startswith(“BODY:”):
body_ar = line.replace(“BODY:”, “”).strip()
return title_ar or title, body_ar or summary
except Exception as e:
print(f”⚠️ خطأ Gemini: {e}”)
return title, summary

# ===================== تنسيق المنشور =====================

def format_post(category, item):
title_ar, body_ar = rewrite_arabic(category, item[“title”], item[“summary”])
hashtags = HASHTAGS.get(category, “#أخبار #تقنية”)

```
post = (
    f"<b>{title_ar}</b>\n\n"
    f"{body_ar}\n\n"
    f"🔗 {item['link']}\n\n"
    f"{hashtags}"
)
return post
```

# ===================== إرسال لتلقرام =====================

def send_telegram(message):
url     = f”https://api.telegram.org/bot{BOT_TOKEN}/sendMessage”
payload = {
“chat_id”:                  CHAT_ID,
“text”:                     message,
“parse_mode”:               “HTML”,
“disable_web_page_preview”: False,
}
try:
r = requests.post(url, json=payload, timeout=15)
if not r.ok:
print(f”⚠️ تلقرام رفض: {r.text}”)
return r.ok
except Exception as e:
print(f”⚠️ خطأ إرسال: {e}”)
return False

# ===================== التشغيل الرئيسي =====================

def main():
today = datetime.now().strftime(”%Y/%m/%d”)
print(f”🚀 بدء الإرسال - {today}”)

```
# ترويسة اليوم
send_telegram(
    f"📰 <b>ملخص أخبار اليوم</b>\n"
    f"📅 {today}\n"
    f"━━━━━━━━━━━━━━━━━━━━\n"
    f"مال • أعمال • ذكاء اصطناعي • تقنية"
)
time.sleep(2)

for category, feeds in RSS_FEEDS.items():
    all_items = []
    for feed_url in feeds:
        items = fetch_news(feed_url, max_items=2)
        all_items.extend(items)
        if len(all_items) >= 2:
            break

    if not all_items:
        continue

    # عنوان الفئة
    send_telegram(f"\n{category}\n━━━━━━━━━━━━━━━━━━━━")
    time.sleep(1)

    for item in all_items[:2]:
        post = format_post(category, item)
        success = send_telegram(post)
        status  = "✅" if success else "❌"
        print(f"{status} {item['title'][:60]}")
        time.sleep(3)  # تجنب rate limit تلقرام

# ختام
send_telegram("✅ <b>انتهى ملخص اليوم</b>\nشارك ما يناسبك على X 🔁")
print("✅ اكتمل الإرسال")
```

if **name** == “**main**”:
main()
