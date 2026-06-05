import os
import time
import requests
import feedparser
import re

# ================= الإعدادات الأساسية =================
BOT_TOKEN = os.environ.get("BOT_TOKEN")
CHAT_ID = os.environ.get("CHAT_ID")
OPENROUTER_KEY = os.environ.get("OPENROUTER_KEY")
MODEL = "nvidia/nemotron-3-super-120b-a12b:free"

FEEDS = {
    "The Rundown AI": "https://www.therundown.ai/feed",
    "AI Valley": "https://www.theaivalley.com/feed"
}

# هوية المتصفح للتنكر
HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
}

HISTORY_FILE = "articles_history.txt"

def load_history():
    if os.path.exists(HISTORY_FILE):
        with open(HISTORY_FILE, "r", encoding="utf-8") as f:
            return set(f.read().splitlines())
    return set()

def save_history(article_id):
    with open(HISTORY_FILE, "a", encoding="utf-8") as f:
        f.write(article_id + "\n")

def clean_html(raw_html):
    clean_text = re.sub(r'<.*?>', ' ', raw_html)
    return ' '.join(clean_text.split())

def translate_article(text, source_name):
    prompt = (
        f"ترجم الخبر التالي من {source_name} إلى العربية بأسلوب تقني وجذاب، احذف الإعلانات والمقدمات:\n\n{text[:6000]}"
    )
    headers = {"Authorization": f"Bearer {OPENROUTER_KEY}", "Content-Type": "application/json"}
    payload = {"model": MODEL, "messages": [{"role": "user", "content": prompt}]}
    try:
        response = requests.post("https://openrouter.ai/api/v1/chat/completions", headers=headers, json=payload, timeout=40)
        return response.json()['choices'][0]['message']['content'].strip() if response.status_code == 200 else None
    except: return None

def send_to_telegram(text):
    max_length = 4000
    parts = [text[i:i+max_length] for i in range(0, len(text), max_length)]
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
    for i, part in enumerate(parts):
        msg = f"📄 (الجزء {i+1}/{len(parts)})\n\n{part}" if len(parts) > 1 else part
        requests.post(url, json={"chat_id": CHAT_ID, "text": msg, "disable_web_page_preview": True})
        time.sleep(2)

def main():
    history = load_history()
    for name, url in FEEDS.items():
        print(f"🔍 جاري فحص: {name}...")
        try:
            response = requests.get(url, headers=HEADERS, timeout=15)
            feed = feedparser.parse(response.content)
            if not feed.entries:
                print(f"⚠️ لم يتم العثور على مقالات في {name}.")
                continue
            
            entry = feed.entries[0]
            article_id = entry.get("id", entry.link)
            if article_id in history: continue
            
            print(f"📰 ترجمة: {entry.title}")
            content = clean_html(entry.get("description", "") or entry.get("content", [{"value": ""}])[0]["value"])
            translated = translate_article(content, name)
            
            if translated:
                send_to_telegram(f"🌟 **أخبار {name}** 🌟\n\n{translated}\n\n🔗 {entry.link}")
                save_history(article_id)
        except Exception as e:
            print(f"❌ خطأ: {e}")

if __name__ == "__main__":
    main()
