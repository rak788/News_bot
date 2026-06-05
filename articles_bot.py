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
    "The Rundown AI": "https://kill-the-newsletter.com/feeds/vmpt1xkvkh09g4qleuyk.xml",
    "AI Valley": "https://kill-the-newsletter.com/feeds/x5iil8j3p08xnyzbxc4l.xml"
}

# هوية المتصفح لتخطي الحماية
HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
    'Accept': 'application/rss+xml, application/xml, text/xml, */*'
}

HISTORY_FILE = "articles_history.txt"

# ================= الدوال المساعدة =================

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
        f"هذه نشرة بريدية تقنية من {source_name}. "
        "أريدك أن تترجم جميع الأخبار والأدوات المذكورة فيها بالكامل إلى اللغة العربية بأسلوب صحفي تقني جذاب. "
        "شروط هامة: احذف الإعلانات، المقدمات الترحيبية، واستخدم نقاط وتنسيق واضح.\n\n"
        f"النص الأصلي:\n{text[:6000]}"
    )
    headers = {"Authorization": f"Bearer {OPENROUTER_KEY}", "Content-Type": "application/json"}
    payload = {"model": MODEL, "messages": [{"role": "user", "content": prompt}]}
    
    try:
        response = requests.post("https://openrouter.ai/api/v1/chat/completions", headers=headers, json=payload, timeout=40)
        if response.status_code == 200:
            return response.json()['choices'][0]['message']['content'].strip()
    except Exception as e:
        print(f"❌ خطأ في الاتصال بالذكاء الاصطناعي: {e}")
    return None

def send_to_telegram(text):
    max_length = 4000
    # تقسيم النص إذا كان طويلاً
    while len(text) > 0:
        part = text[:max_length]
        # إذا كان النص طويلاً نحاول القص عند سطر جديد
        if len(text) > max_length:
            split_index = part.rfind('\n', 0, max_length)
            if split_index != -1:
                part = text[:split_index]
        
        url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
        payload = {"chat_id": CHAT_ID, "text": part, "disable_web_page_preview": True}
        requests.post(url, json=payload)
        
        text = text[len(part):].lstrip()
        time.sleep(2)

# ================= البرنامج الرئيسي =================

def main():
    history = load_history()
    
    for name, url in FEEDS.items():
        print(f"🔍 جاري فحص: {name}...")
        try:
            response = requests.get(url, headers=HEADERS, timeout=20)
            feed = feedparser.parse(response.content)
            
            if not feed.entries:
                print(f"⚠️ لم يتم العثور على مقالات في {name}.")
                continue
            
            latest_entry = feed.entries[0]
            article_id = latest_entry.get("id", latest_entry.link)
            
            if article_id in history:
                print(f"💤 المقال الأخير من {name} تم إرساله مسبقاً.")
                continue
            
            print(f"📰 مقال جديد وجدناه: {latest_entry.title}")
            
            raw_content = latest_entry.get("description", "") or latest_entry.get("content", [{"value": ""}])[0]["value"]
            clean_text = clean_html(raw_content)
            
            if len(clean_text) < 100:
                print("⚠️ محتوى المقال قصير جداً، تخطي...")
                continue
            
            print("🤖 جاري الترجمة...")
            translated_text = translate_article(clean_text, name)
            
            if translated_text:
                final_message = f"🌟 **أحدث أخبار {name}** 🌟\n\n{translated_text}\n\n🔗 [رابط المصدر]({latest_entry.link})"
                send_to_telegram(final_message)
                save_history(article_id)
                print("✅ تمت العملية بنجاح.")
            
        except Exception as e:
            print(f"❌ خطأ تقني في {name}: {e}")
            
        time.sleep(5)

if __name__ == "__main__":
    main()
