import feedparser
import requests
import time
import os
import random
from datetime import datetime

# ========================================================
# 1. إعدادات البوت والبيانات
# ========================================================
BOT_TOKEN = os.environ.get("BOT_TOKEN", "")
CHAT_ID = "-1003951245443" # تم وضع الـ Chat ID الخاص بقناتك السرية هنا مباشرة
OPENROUTER_KEY = os.environ.get("OPENROUTER_KEY", "")

OPENROUTER_URL = "https://openrouter.ai/api/v1/chat/completions"
MODEL = "openai/gpt-oss-120b:free"

# مصادر النخبة (Newsletters & Reddit) للحصول على المحتوى الثقيل
SOURCES = {
    "DEEP_TECH": [
        "https://www.reddit.com/r/LocalLLaMA/top/.rss?t=day",
        "https://www.reddit.com/r/MachineLearning/top/.rss?t=day",
        "https://buttondown.email/ainews/rss"
    ],
    "PROMPT_ART": [
        "https://www.reddit.com/r/PromptEngineering/top/.rss?t=day",
        "https://www.reddit.com/r/StableDiffusion/top/.rss?t=day",
        "https://www.reddit.com/r/midjourney/top/.rss?t=day",
        "https://civitai.com/api/v1/feeds/models"
    ],
    "TOOLS_NEWSLETTERS": [
        "https://www.producthunt.com/feed",
        "https://the-decoder.com/feed/",
        "https://maginative.com/rss/"
    ]
}

def fetch_feed(urls, max_per_feed=10):
    items = []
    headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"}
    for url in urls:
        try:
            feed = feedparser.parse(url, request_headers=headers)
            for entry in feed.entries[:max_per_feed]:
                title = entry.get("title", "").strip()
                summary = entry.get("summary", entry.get("description", "")).strip()
                link = entry.get("link", "").strip()
                if title and link:
                    items.append(f"Title: {title}\nDetails: {summary[:800]}")
        except Exception as e:
            print(f"Error fetching RSS ({url}): {str(e)}")
    return items

# ========================================================
# 2. محرك الذكاء الاصطناعي (مع مقاومة الضغط)
# ========================================================
def ask_ai(system_prompt, content_data, retries=3, delay=4):
    headers = {
        "Authorization": f"Bearer {OPENROUTER_KEY}",
        "Content-Type": "application/json",
    }
    
    full_prompt = f"{system_prompt}\n\nهنا المادة الخام (الأخبار والأدوات):\n{content_data}"
    
    payload = {
        "model": MODEL,
        "messages": [{"role": "user", "content": full_prompt}],
        "max_tokens": 1500,
        "temperature": 0.7
    }
    
    for attempt in range(retries):
        try:
            r = requests.post(OPENROUTER_URL, headers=headers, json=payload, timeout=45)
            if r.ok:
                text = r.json()["choices"][0]["message"]["content"].strip()
                # تنظيف النص من علامات الماركداون البرمجية إن وجدت ليقبله تليجرام
                text = text.replace("```html", "").replace("
```", "").strip()
                return text
            
            if r.status_code in [503, 429]:
                print(f"Server busy. Retrying... ({attempt+1}/{retries})")
                time.sleep(delay)
                continue
            else:
                print(f"AI error: {r.status_code}")
                return None
        except Exception as e:
            print(f"AI connection error: {str(e)}")
            time.sleep(delay)
    return None

def send_telegram(message):
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
    payload = {
        "chat_id": CHAT_ID,
        "text": message,
        "parse_mode": "HTML",
        "disable_web_page_preview": True,
    }
    try:
        r = requests.post(url, json=payload, timeout=15)
        if not r.ok:
            print(f"Telegram formatting error. Fallback to plain text. Error: {r.text}")
            payload["parse_mode"] = None # محاولة الإرسال بدون تنسيق إذا فشل الـ HTML
            requests.post(url, json=payload, timeout=15)
        return True
    except Exception as e:
        print(f"Telegram error: {str(e)}")
        return False

# ========================================================
# 3. قوالب المحتوى الثقيل (هندسة الأوامر المتقدمة)
# ========================================================

def get_workshop_post(data_pool):
    prompt = (
        "أنت خبير عربي تقني من النخبة. استخرج أداة أو تقنية واحدة من النص المرفق واكتب عنها 'ورشة عمل مصغرة'.\n"
        "الجمهور: صناع محتوى ومحترفون عرب يبحثون عن القيمة العملية لا مجرد الأخبار.\n"
        "يجب أن يكون الناتج النهائي بتنسيق HTML متوافق مع Telegram (استخدم <b> للخط العريض فقط، لا تستخدم **).\n\n"
        "هيكل المنشور المطلوب:\n"
        "🛠️ <b>[اسم الأداة أو التقنية المذهلة]</b>\n\n"
        "💡 <b>الزبدة:</b> (شرح الفكرة في سطرين بأسلوب جذاب).\n\n"
        "🎯 <b>كيف تستفيد منها عملياً؟ (ورشة سريعة):</b>\n"
        "1. <b>الخطوة الأولى:</b> (شرح الخطوة)\n"
        "2. <b>الخطوة الثانية:</b> (شرح الخطوة)\n"
        "3. <b>الخطوة الثالثة:</b> (شرح الخطوة)\n\n"
        "💎 <b>نصيحة الخبير:</b> (سر أو تريك إضافي للمحترفين)."
    )
    return ask_ai(prompt, "\n\n".join(random.sample(data_pool, min(5, len(data_pool)))))

def get_prompt_library_post(data_pool):
    prompt = (
        "أنت مهندس أوامر (Prompt Engineer) عبقري. استلهم من النص المرفق ستايل تصميم أو فكرة معقدة، واصنع منها برومبت إنجليزي عملاق واحترافي.\n"
        "يجب أن يكون الناتج بتنسيق HTML لتليجرام. البرومبت الإنجليزي يجب أن يوضع بالكامل داخل علامات <code>البرومبت هنا</code> لكي ينسخه المستخدم بضغطة زر.\n\n"
        "هيكل المنشور المطلوب:\n"
        "✨ <b>مكتبة الأوامر | ستايل [اسم الستايل الفني/الفكرة]</b>\n\n"
        "🧠 <b>عن ماذا نتحدث؟</b> (شرح تأثير هذا البرومبت ولماذا هو مميز).\n\n"
        "⚙️ <b>البرومبت الاحترافي (اضغط للنسخ):</b>\n"
        "<code>[هنا تكتب البرومبت الإنجليزي الطويل جداً والمفصل باللغة الإنجليزية فقط]</code>\n\n"
        "🎨 <b>كيف تعدل عليه؟</b> (اشرح بالعربي الكلمات التي يمكن للمستخدم تغييرها داخل البرومبت مثل الألوان، الإضاءة، الموضوع)."
    )
    return ask_ai(prompt, "\n\n".join(random.sample(data_pool, min(5, len(data_pool)))))

def get_content_idea_post(data_pool):
    prompt = (
        "أنت مخرج إبداعي خبير في السوشيال ميديا. استخرج ترند أو أداة من النص المرفق، وحولها إلى 'فكرة فيديو فيرال (Reel/TikTok)'.\n"
        "يجب أن يكون الناتج بتنسيق HTML لتليجرام.\n\n"
        "هيكل المنشور المطلوب:\n"
        "🎬 <b>ترند المحتوى | فكرة فيديو ستكسر الخوارزميات</b>\n\n"
        "🔥 <b>الفكرة:</b> (عنوان الفيديو).\n\n"
        "🎣 <b>أقوى 3 جمل خطافية (Hooks) لتبدأ بها:</b>\n"
        "• <b>الخيار 1:</b> ...\n"
        "• <b>الخيار 2:</b> ...\n"
        "• <b>الخيار 3:</b> ...\n\n"
        "📝 <b>السيناريو السريع:</b> (ماذا يعرض في الشاشة وماذا يقول في الثواني الأولى والوسطى والنهاية)."
    )
    return ask_ai(prompt, "\n\n".join(random.sample(data_pool, min(5, len(data_pool)))))

def get_deep_news_post(data_pool):
    prompt = (
        "أنت محلل تقني عميق. استخرج أهم خبر تحديث ذكاء اصطناعي من النص، واكتب عنه تحليلاً قصيراً يهم المحترفين.\n"
        "يجب أن يكون الناتج بتنسيق HTML لتليجرام.\n\n"
        "هيكل المنشور المطلوب:\n"
        "📰 <b>رادار الذكاء الاصطناعي | [عنوان الخبر الصادم أو المهم]</b>\n\n"
        "🔍 <b>ماذا حدث بالضبط؟</b> (شرح الخبر بدون حشو).\n\n"
        "⚠️ <b>لماذا هذا مهم لك؟ (So What?):</b> (كيف سيؤثر هذا الخبر على عمل صناع المحتوى والمصممين، هل يهدد وظائفهم أم يسهلها؟)."
    )
    return ask_ai(prompt, "\n\n".join(random.sample(data_pool, min(5, len(data_pool)))))

# ========================================================
# 4. دالة التشغيل الرئيسية
# ========================================================
def main():
    print("Starting Elite AI Content Curator...")
    
    send_telegram(f"🔄 <b>جاري سحب وطبخ المحتوى الثقيل ليوم:</b> {datetime.now().strftime('%Y-%m-%d')}\n<i>الرجاء الانتظار قليلاً...</i>")
    
    # سحب المادة الخام
    deep_tech_data = fetch_feed(SOURCES["DEEP_TECH"])
    prompt_data = fetch_feed(SOURCES["PROMPT_ART"])
    tools_data = fetch_feed(SOURCES["TOOLS_NEWSLETTERS"])
    
    all_data = deep_tech_data + prompt_data + tools_data
    if not all_data:
        send_telegram("❌ فشل في جلب البيانات من المصادر اليوم.")
        return

    # إنشاء 8 مسودات دسمة للقناة السرية
    tasks = [
        ("ورشة عمل 1", get_workshop_post, tools_data),
        ("ورشة عمل 2", get_workshop_post, all_data),
        ("مكتبة أوامر 1", get_prompt_library_post, prompt_data),
        ("مكتبة أوامر 2", get_prompt_library_post, prompt_data),
        ("فكرة محتوى 1", get_content_idea_post, deep_tech_data + tools_data),
        ("فكرة محتوى 2", get_content_idea_post, all_data),
        ("تحليل خبر 1", get_deep_news_post, deep_tech_data),
        ("تحليل خبر 2", get_deep_news_post, tools_data),
    ]

    success_count = 0
    for name, func, data in tasks:
        print(f"Generating: {name}...")
        post = func(data)
        if post:
            # إضافة فاصل بصري واسم القسم
            final_post = f"📌 <b>[ مسودة: {name} ]</b>\n━━━━━━━━━━━━━━━━━━━━\n\n{post}"
            if send_telegram(final_post):
                success_count += 1
        time.sleep(10) # راحة للسيرفر لتجنب الحظر

    send_telegram(f"✅ <b>تم الانتهاء!</b>\nتم تجهيز <b>{success_count}</b> منشورات دسمة. تصفحها، اختر الأفضل، وانسخه لقناتك العامة لتفجير التفاعل! 🚀")
    print("Done generating all elite content.")

if __name__ == "__main__":
    main()
