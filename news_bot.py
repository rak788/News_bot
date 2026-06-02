import feedparser
import requests
import re
import time
import os
from datetime import datetime
import random

BOT_TOKEN = os.environ.get("BOT_TOKEN", "")
CHAT_ID = os.environ.get("CHAT_ID", "")
OPENROUTER_KEY = os.environ.get("OPENROUTER_KEY", "")

OPENROUTER_URL = "https://openrouter.ai/api/v1/chat/completions"
MODEL = "openai/gpt-oss-120b:free"

# ========================================================
# 1. المصادر المفتوحة والمضاعفة (تخص صناعة المحتوى فقط)
# ========================================================
SOURCES = {
    # مدونات ومقالات إبداعية متخصصة في الـ AI التوليدي (بديل تويتر)
    "ARTICLES": [
        "https://the-decoder.com/creative/feed/",  # قسم الإبداع وصناعة الأفلام والصور في ذي ديكودر
        "https://maginative.com/rss/",              # موقع متخصص بالكامل في التصميم والسينما والذكاء الاصطناعي
        "https://civitai.com/api/v1/feeds/models"   # خلاصة موقع Civitai الرسمي لأحدث موديلات وبرومبتات الصور
    ],
    # مجتمعات رديت الإبداعية (تم رفع الحد الأقصى لجلب كم ضخم من البيانات للعصف الذهني)
    "REDDIT_COMMUNITIES": [
        "https://www.reddit.com/r/midjourney/top/.rss?t=day",
        "https://www.reddit.com/r/StableDiffusion/top/.rss?t=day",
        "https://www.reddit.com/r/aivideo/top/.rss?t=day",
        "https://www.reddit.com/r/PromptEngineering/top/.rss?t=day"
    ],
    # منصة المنتجات لاستخراج أدوات المونتاج، الصوت، والصناعة المرئية
    "TOOLS": [
        "https://www.producthunt.com/feed"
    ]
}

def fetch_feed(urls, max_per_feed=15): # تم رفع الحد إلى 15 منشوراً من كل مصدر لمضاعفة المحتوى
    items = []
    for url in urls:
        try:
            # استخدام Header احترافي لتجنب أي حظر من المواقع
            headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"}
            feed = feedparser.parse(url, request_headers=headers)
            for entry in feed.entries[:max_per_feed]:
                title = entry.get("title", "").strip()
                summary = entry.get("summary", entry.get("description", "")).strip()
                link = entry.get("link", "").strip()
                # تنظيف النصوص من وسوم HTML وتقليص حجمها لتغذية الذكاء الاصطناعي بنص نظيف
                summary = re.sub(r'<[^>]+>', '', summary)[:500].strip()
                if title and link:
                    items.append({"title": title, "summary": summary, "link": link})
        except Exception as e:
            print(f"Error fetching RSS ({url}): {str(e)}")
    return items

# دالة خبيرة لجلب مشاريع GitHub الإبداعية فقط (توليد الصور، الفيديو، تحريك الوجوه، الصوت)
def fetch_github_creative_trending(max_items=15): # جلب 15 مشروعاً دسمًا
    items = []
    try:
        headers = {"User-Agent": "Mozilla/5.0 (compatible; CreativeBot/1.0)"}
        # استعلام ذكي يستهدف مستودعات بايثون الخاصة بالذكاء الاصطناعي التوليدي والصور والفيديو والأعلى نجوماً اليوم
        url = "https://api.github.com/search/repositories?q=language:python+topic:generative-ai+topic:image-generation+topic:video-generation&sort=stars&order=desc&per_page=20"
        
        r = requests.get(url, headers=headers, timeout=15)
        if r.ok:
            repos = r.json().get("items", [])
            for repo in repos[:max_items]:
                title = f"GitHub Project: {repo.get('full_name')}"
                summary = repo.get("description", "No description available.")
                link = repo.get("html_url")
                if title and link:
                    items.append({"title": title, "summary": summary, "link": link})
        else:
            print(f"GitHub API Error: {r.status_code}")
    except Exception as e:
        print("GitHub Fetch Error: " + str(e))
    return items

def ask_ai(prompt):
    try:
        headers = {
            "Authorization": "Bearer " + OPENROUTER_KEY,
            "Content-Type": "application/json",
        }
        payload = {
            "model": MODEL,
            "messages": [{"role": "user", "content": prompt}],
            "max_tokens": 1200, # رفع الحد لضمان صياغة منشورات طويلة ودسمة دون انقطاع النص
            "temperature": 0.6 # موازنة مثالية بين الدقة التقنية والابتكار الإبداعي
        }
        r = requests.post(OPENROUTER_URL, headers=headers, json=payload, timeout=40)
        if r.ok:
            return r.json()["choices"][0]["message"]["content"].strip()
        else:
            print("AI error: " + str(r.status_code) + " " + r.text[:200])
            return ""
    except Exception as e:
        print("AI error: " + str(e))
        return ""

def send_telegram(message):
    url = "https://api.telegram.org/bot" + BOT_TOKEN + "/sendMessage"
    payload = {
        "chat_id": CHAT_ID,
        "text": message,
        "parse_mode": "HTML",
        "disable_web_page_preview": True,
    }
    try:
        r = requests.post(url, json=payload, timeout=15)
        return r.ok
    except Exception as e:
        print("Telegram error: " + str(e))
        return False

def parse_ai_response(text, keys):
    data = {key: [] for key in keys}
    current_key = None
    
    for line in text.splitlines():
        clean_line = line.replace("**", "").strip()
        if clean_line.startswith("- ") or clean_line.startswith("* "):
            clean_line = clean_line[2:].strip()
            
        found_key = False
        for key in keys:
            if clean_line.startswith(key + ":"):
                current_key = key
                value = clean_line.split(key + ":", 1)[1].strip()
                if value:
                    data[current_key].append(value)
                found_key = True
                break
                
        if not found_key and current_key and clean_line:
            data[current_key].append(clean_line)
            
    return {k: "\n".join(v).strip() for k, v in data.items()}

# ========================================================
# 2. هندسة الأوامر (Prompts) الموجهة لصناعة المحتوى الإبداعي
# ========================================================

def make_content_idea_post(items):
    if not items:
        return None
    titles = "\n".join([x["title"] + ": " + x["summary"][:200] for x in items])
    
    # فلترة صارمة لمنع الأخبار الجافة والاستحواذات وتوجيه الذكاء الاصطناعي للتوسيع والابتكار
    prompt = (
        "أنت المخرج الإبداعي وخبير السوشيال ميديا الأول في صناعة وفيديوهات الذكاء الاصطناعي التوليدي.\n"
        "إليك كمية ضخمة من المقالات والتوجهات وفيديوهات الـ AI الصاعدة اليوم عالمياً:\n"
        + titles + "\n\n"
        "تعليمات صارمة:\n"
        "1. تجاهل تماماً واحظر أي أخبار عامة مثل: استحواذ شركات، استثمارات، تمويل، مشاكل قانونية، أو مجرد طرح أسماء نماذج جافة.\n"
        "2. ركز 100% على (طرق صناعة المحتوى، الفيديوهات التوليدية، الخدع البصرية، الدمج بين الأدوات).\n"
        "3. البيانات الممررة إليك قد تكون نصوصاً قصيرة، دورك هنا هو الابتكار والتوسيع وتقديم الفكرة بشكل كامل ودسم ومفصل جداً.\n\n"
        "اكتب باللغة العربية الفصحى المبسطة وبدون مقدمات الهياكل التالية:\n"
        "IDEA: عنوان ملهم ومبتكر لفكرة فيديو قصير (Reel/TikTok/Short) بناءً على هذه المواد\n"
        "WHY: تحليل دسم وعميق يوضح لماذا هذا التوجه أو الفكرة ستضرب ترند وتجلب ملايين المشاهدات اليوم\n"
        "STEPS: دليل عملي تطبيقي ومفصل جداً (خطوة بخطوة) يشرح للمتابع كيف يصنع هذا الفيديو (ما هي الأدوات التوليدية المستخدمة للفيديو والصوت، وكيف يدمجها؟)\n"
        "HOOK: اكتب 3 خيارات لجمل افتتاحية خطافية (Hooks) قوية ومثيرة ومكتوبة باللهجة البيضاء الجاذبة يبدأ بها الكرييتور الفيديو لمنع المشاهد من التمرير"
    )
    result = ask_ai(prompt)
    if not result:
        return None

    parsed = parse_ai_response(result, ["IDEA", "WHY", "STEPS", "HOOK"])
    if not parsed["IDEA"]:
        return None

    return (
        "🎬 <b>رادار الترند وفكرة محتوى اليوم</b>\n"
        "🔥 <b>" + parsed["IDEA"] + "</b>\n\n"
        + "📈 <b>لماذا هذا الترند قوي جداً؟</b>\n" + parsed["WHY"] + "\n\n"
        + "🛠️ <b>دليل الحرفيين (كيف تصنع الفيديو خطوة بخطوة):</b>\n" + parsed["STEPS"] + "\n\n"
        + "🎣 <b>جمل البداية الخطافية لإمساك المشاهد (اختر منها):</b>\n"
        + parsed["HOOK"] + "\n\n"
        + "#صناعة_محتوى #AIVideo #تيك_توك #صناع_المحتوى"
    )

def make_prompt_post(items):
    if not items:
        return None
    titles = "\n".join([x["title"] + ": " + x["summary"][:200] for x in items])
    
    prompt = (
        "أنت مهندس أوامر (Prompt Engineer) وفنان رقمي محترف متخصص في أدوات الصور (Midjourney, Stable Diffusion, Civitai).\n"
        "إليك أحدث المنشورات والنماذج الرائجة من مجتمعات التصميم الفني العالمية:\n"
        + titles + "\n\n"
        "تعليمات صارمة:\n"
        "1. ادمج الأفكار الممررة إليك واستخلص منها 'لغة تصميم أو ستايل فني ساخن جداً' ومطلوب في السوشيال ميديا الآن.\n"
        "2. قم بابتكار وتوسيع برومبت إنجليزي طويل، دقيق، احترافي، ومليء بالتفاصيل (الإضاءة، زاوية الكاميرا، جودة الألوان، الستايل الفني).\n\n"
        "اكتب بالفصحى وبدون مقدمات الهياكل التالية:\n"
        "STYLE: اسم الستايل الفني الرائج اليوم والهدف منه\n"
        "USE: أفكار إبداعية وتطبيقية لصناع المحتوى لاستغلال هذا الستايل في حساباتهم (لجذب المتابعين أو التصميم التجاري)\n"
        "PROMPT: اكتب البرومبت (Prompt) باللغة الإنجليزية بالكامل داخل سطر واحد، ليكون طويلاً، دقيقاً وجاهزاً تماماً للنسخ\n"
        "TIPS: نصائح برمجية وسرية لتعديل الكلمات المفتاحية أو الأبعاد أو الإعدادات داخل الأداة للحصول على نتائج مبهرة وخرافية"
    )
    result = ask_ai(prompt)
    if not result:
        return None

    parsed = parse_ai_response(result, ["STYLE", "USE", "PROMPT", "TIPS"])
    if not parsed["STYLE"]:
        return None

    return (
        "✨ <b•برومبت اليوم السحري (الهام من Reddit &amp; Civitai)</b>\n"
        "🎨 الستايل الفني: <b>" + parsed["STYLE"] + "</b>\n\n"
        + "🎯 <b>كيف تستغله في محتواك؟</b>\n" + parsed["USE"] + "\n\n"
        + "🧠 <b>البرومبت الاحترافي (انسخ وجرب فوراً):</b>\n"
        + "<code>" + parsed["PROMPT"] + "</code>\n\n"
        + "💡 <b>أسرار التعديل وهندسة الأمر:</b>\n" + parsed["TIPS"] + "\n\n"
        + "#Midjourney #Civitai #هندسة_الأوامر #تصميم_AI"
    )

def make_creator_tool_post(items):
    if not items:
        return None
    titles = "\n".join([x["title"] + ": " + x["summary"][:150] for x in items])
    prompt = (
        "أنت مستشار تقني تبحث عن أدوات الذكاء الاصطناعي لرفع إنتاجية ومبيعات صناع المحتوى.\n"
        "إليك أحدث الأدوات المطروحة تقنياً اليوم:\n"
        + titles + "\n\n"
        "تعليمات صارمة:\n"
        "1. اختر أداة واحدة فقط تكون مخصصة وحصرياً لـ (المونتاج، تعديل وهندسة الصوت، توليد السكربتات، تحريك الصور، تنظيم محتوى الكرييتورز).\n"
        "2. احظر وتجاهل تماماً مكاتب البرمجة، لغات البرد، أدوات الـ Devops، أو البرمجيات المعقدة.\n\n"
        "اكتب بالفصحى وبدون مقدمات:\n"
        "NAME: اسم الأداة\n"
        "VALUE: كيف ستختصر هذه الأداة ساعات من العمل لصانع المحتوى؟ (اشرح الميزة التنافسية لها بذكاء)\n"
        "USE_CASE: سيناريو ومثال عملي وحقيقي لكيفية استخدامها في صناعة فيديو أو منشور\n"
        "FOR: حدد بدقة من هي الفئة المستفيدة (يوتيوبرز، بودكاسترز، مصممو تيك توك..)"
    )
    result = ask_ai(prompt)
    if not result:
        return None

    parsed = parse_ai_response(result, ["NAME", "VALUE", "USE_CASE", "FOR"])
    if not parsed["NAME"]:
        return None

    return (
        "🛠️ <b>ترسانة الكرييتورز | أداة اليوم 🤖</b>\n\n"
        + "⭐ <b>" + parsed["NAME"] + "</b>\n\n"
        + "⚡ <b>السحر والإنتاجية (كيف تختصر وقتك؟):</b>\n" + parsed["VALUE"] + "\n\n"
        + "🎯 <b>تطبيق سيناريو عملي:</b>\n" + parsed["USE_CASE"] + "\n\n"
        + "👥 <b>من يحتاج هذه الأداة فوراً؟</b>\n" + parsed["FOR"] + "\n\n"
        + "#أدوات_المحتوى #إنتاجية #المونتاج_الذكي"
    )

# ========================================================
# 3. دالة التشغيل الرئيسية والتحكم بالبيانات
# ========================================================
def main():
    today = datetime.now().strftime("%Y/%m/%d")
    print(f"Starting Elite Creator Bot - {today}")

    header = (
        "🎨 <b>أكاديمية صناع المحتوى بالذكاء الاصطناعي</b>\n"
        "📅 " + today + "\n"
        "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
        "✨ برومبتات احترافية • 🎬 أفكار فيديوهات وترندات • 🛠️ أدوات الإنتاجية المرئية"
    )
    send_telegram(header)
    time.sleep(3)

    # أ) جلب كميات ضخمة من البيانات النظيفة والمستقرة
    article_items = fetch_feed(SOURCES["ARTICLES"], max_per_feed=10)
    reddit_items = fetch_feed(SOURCES["REDDIT_COMMUNITIES"], max_per_feed=15)
    github_items = fetch_github_creative_trending(max_items=15)
    tool_items = fetch_feed(SOURCES["TOOLS"], max_per_feed=15)
    
    # ب) الدمج الذكي للبيانات لتغذية الأقسام
    # لقسم الفيديوهات والترندات: ندمج المقالات المتخصصة الإبداعية + مشاريع جيتهاب الإبداعية + مجتمعات رديت للفيديو والبرومبت
    content_pool = article_items + github_items + reddit_items
    random.shuffle(content_pool)
    
    # لقسم برومبتات الصور: نركز على رديت وسيفيت آي لضمان خروج لغة تصميمية عبقرية
    prompt_pool = reddit_items + article_items
    random.shuffle(prompt_pool)

    print(f"Data Pools loaded successfully - Total Content Pool: {len(content_pool)} items.")

    # 1. إرسال منشور فكرة محتوى الفيديو (ترندات دسمة وموسعة)
    send_telegram("🎬 <b>رادار الترند وأفكار الفيديوهات القصيرة</b>\n━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")
    time.sleep(2)
    post = make_content_idea_post(content_pool)
    if post:
        send_telegram(post)
        print("Success: Generated Elite Content Idea Post")
    time.sleep(5)

    # 2. إرسال منشور البرومبت السحري الطويل والجاهز للنسخ
    send_telegram("✨ <b>إلهام التصميم الرقمي وهندسة الأوامر</b>\n━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")
    time.sleep(2)
    post = make_prompt_post(prompt_pool)
    if post:
        send_telegram(post)
        print("Success: Generated Long Prompt Post")
    time.sleep(5)

    # 3. إرسال أداة الإنتاجية الإبداعية المفلترة
    send_telegram("🛠️ <b>أسلحة الكرييتورز (أدوات صناعة الميديا)</b>\n━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")
    time.sleep(2)
    post = make_creator_tool_post(tool_items)
    if post:
        send_telegram(post)
        print("Success: Generated Creator Tool Post")
    time.sleep(5)

    footer = (
        "✅ <b>جرعة الإلهام اليومية اكتملت بنجاح</b>\n"
        "المصادر غنية ومحدثة تلقائياً. حان الوقت لتبهر جمهورك؛ ابدأ بصناعة محتواك الآن! 🚀"
    )
    send_telegram(footer)
    print("Execution Finished Smoothly.")

if __name__ == "__main__":
    main()
