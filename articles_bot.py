import os
import time
import requests
import feedparser
import re

# ================= الإعدادات الأساسية =================
BOT_TOKEN = os.environ.get("BOT_TOKEN")
CHAT_ID = os.environ.get("CHAT_ID")
OPENROUTER_KEY = os.environ.get("OPENROUTER_KEY")
MODEL = "google/gemma-2-27b-it:free" # النموذج المستقر والمجاني

# روابط RSS للنشرات البريدية
FEEDS = {
    "The Rundown AI": "https://www.therundown.ai/rss.xml",
    "AI Valley": "https://www.theaivalley.com/rss.xml"
}

HISTORY_FILE = "articles_history.txt"

# ================= الدوال المساعدة =================

def load_history():
    """تحميل سجل المقالات التي تم إرسالها مسبقاً لتجنب التكرار"""
    if os.path.exists(HISTORY_FILE):
        with open(HISTORY_FILE, "r", encoding="utf-8") as f:
            return set(f.read().splitlines())
    return set()

def save_history(article_id):
    """حفظ معرف المقال الجديد في السجل"""
    with open(HISTORY_FILE, "a", encoding="utf-8") as f:
        f.write(article_id + "\n")

def clean_html(raw_html):
    """تنظيف النص من أكواد HTML لتقليل استهلاك الـ Tokens"""
    clean_text = re.sub(r'<.*?>', ' ', raw_html)
    return ' '.join(clean_text.split())

def translate_article(text, source_name):
    """إرسال النص إلى OpenRouter لترجمته وتلخيصه حسب الشروط"""
    prompt = (
        f"هذه نشرة بريدية تقنية من {source_name}. "
        "أريدك أن تترجم **جميع الأخبار والأدوات المذكورة فيها بالكامل إلى اللغة العربية** دون أن تحذف أي معلومة مفيدة. "
        "شروط هامة:\n"
        "1. احذف أي إعلانات (Sponsors) أو عروض ترويجية.\n"
        "2. احذف المقدمات والخاتمات الترحيبية.\n"
        "3. استخدم تنسيقاً جذاباً، مع العناوين العريضة، والنقاط (Bullet points)، والإيموجي المناسب.\n"
        "4. لا تقم بالترجمة الحرفية المعقدة، بل صغها بأسلوب صحفي تقني عربي واضح.\n\n"
        f"النص الأصلي:\n{text[:6000]}" # نرسل أول 6000 حرف لتجنب أخطاء حجم النص الطويل جداً
    )
    
    headers = {"Authorization": f"Bearer {OPENROUTER_KEY}", "Content-Type": "application/json"}
    payload = {
        "model": MODEL,
        "messages": [{"role": "user", "content": prompt}]
    }
    
    try:
        response = requests.post("https://openrouter.ai/api/v1/chat/completions", headers=headers, json=payload, timeout=40)
        if response.status_code == 200:
            data = response.json()
            return data['choices'][0]['message']['content'].strip()
        else:
            print(f"❌ خطأ في الترجمة: {response.status_code}")
            return None
    except Exception as e:
        print(f"❌ فشل الاتصال بالذكاء الاصطناعي: {e}")
        return None

def send_to_telegram(text):
    """إرسال النص إلى تليجرام مع ميزة التقسيم التلقائي إذا تجاوز 4000 حرف"""
    max_length = 4000
    parts = []
    
    # التقسيم الذكي للنص
    while len(text) > 0:
        if len(text) <= max_length:
            parts.append(text)
            break
        # البحث عن أقرب سطر جديد لتجنب قص الكلمات في المنتصف
        split_index = text.rfind('\n', 0, max_length)
        if split_index == -1: 
            split_index = max_length
            
        parts.append(text[:split_index])
        text = text[split_index:].lstrip()

    # إرسال الأجزاء بالترتيب
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
    for i, part in enumerate(parts):
        # إضافة ترقيم إذا كانت الرسالة مقسمة
        if len(parts) > 1:
            part = f"📄 (الجزء {i+1}/{len(parts)})\n\n" + part
            
        payload = {"chat_id": CHAT_ID, "text": part, "disable_web_page_preview": True}
        try:
            req = requests.post(url, json=payload)
            if req.status_code == 200:
                print(f"✅ تم إرسال الجزء {i+1} بنجاح!")
            else:
                print(f"❌ فشل الإرسال لتليجرام: {req.text}")
            time.sleep(3) # استراحة 3 ثوانٍ بين الرسائل لتجنب حظر تليجرام
        except Exception as e:
            print(f"❌ خطأ أثناء الإرسال: {e}")

# ================= البرنامج الرئيسي =================

def main():
    history = load_history()
    
    for source_name, feed_url in FEEDS.items():
        print(f"🔍 جاري فحص: {source_name}...")
        feed = feedparser.parse(feed_url)
        
        if not feed.entries:
            print(f"⚠️ لم يتم العثور على مقالات في {source_name} (قد يكون الرابط متوقفاً حالياً).")
            continue
            
        # نأخذ أحدث مقال فقط في كل عملية تشغيل
        latest_entry = feed.entries[0]
        article_id = latest_entry.get("id", latest_entry.link)
        
        if article_id in history:
            print(f"💤 المقال الأخير من {source_name} تم إرساله مسبقاً.")
            continue
            
        print(f"📰 مقال جديد وجدناه: {latest_entry.title}")
        
        # استخراج النص وتنظيفه
        raw_content = latest_entry.get("description", "") or latest_entry.get("content", [{"value": ""}])[0]["value"]
        clean_text = clean_html(raw_content)
        
        # إذا كان النص قصيراً جداً، نتجاهله (قد يكون خطأ من الـ RSS)
        if len(clean_text) < 100:
            print("⚠️ محتوى المقال فارغ أو قصير جداً.")
            continue
            
        print("🤖 جاري إرسال النص للترجمة والتلخيص...")
        translated_text = translate_article(clean_text, source_name)
        
        if translated_text:
            # إضافة المصدر في النهاية
            final_message = f"🌟 **أحدث أخبار {source_name}** 🌟\n\n{translated_text}\n\n🔗 [رابط النشرة الأصلية]({latest_entry.link})"
            send_to_telegram(final_message)
            save_history(article_id)
            print("✅ انتهت العملية بنجاح لهذا المصدر.")
        else:
            print("❌ فشلت عملية الترجمة لهذا المقال.")
            
        # استراحة بين المصدر الأول والثاني لتجنب ضغط الـ API
        print("⏳ استراحة 10 ثوانٍ قبل فحص المصدر التالي...")
        time.sleep(10)

if __name__ == "__main__":
    main()
