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
# 1. المصادر المفتوحة
# ========================================================
SOURCES = {
    "ARTICLES": [
        "https://the-decoder.com/creative/feed/",
        "https://maginative.com/rss/",
        "https://civitai.com/api/v1/feeds/models"
    ],
    "REDDIT_COMMUNITIES": [
        "https://www.reddit.com/r/midjourney/top/.rss?t=day",
        "https://www.reddit.com/r/StableDiffusion/top/.rss?t=day",
        "https://www.reddit.com/r/aivideo/top/.rss?t=day",
        "https://www.reddit.com/r/PromptEngineering/top/.rss?t=day"
    ],
    "TOOLS": [
        "https://www.producthunt.com/feed"
    ]
}

def fetch_feed(urls, max_per_feed=15):
    items = []
    for url in urls:
        try:
            headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"}
            feed = feedparser.parse(url, request_headers=headers)
            for entry in feed.entries[:max_per_feed]:
                title = entry.get("title", "").strip()
                summary = entry.get("summary", entry.get("description", "")).strip()
                link = entry.get("link", "").strip()
                summary = re.sub(r'<[^>]+>', '', summary)[:500].strip()
                if title and link:
                    items.append({"title": title, "summary": summary, "link": link})
        except Exception as e:
            print(f"Error fetching RSS ({url}): {str(e)}")
    return items

def fetch_github_creative_trending(max_items=15):
    items = []
    try:
        headers = {"User-Agent": "Mozilla/5.0 (compatible; CreativeBot/1.0)"}
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
            "max_tokens": 1200,
            "temperature": 0.6
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

# 🌟 تحديث جوهري: دالة معالجة ذكية ومقاومة لكافة أشكال الماركداون والرموز
def parse_ai_response(text, keys):
    data = {key: [] for key in keys}
    current_key = None
    
    for line in text.splitlines():
        clean_line = line.strip()
        if not clean_line:
            continue
            
        found_key = False
        for key in keys:
            # تعبير نمطي يبحث عن الكلمة المفتاحية أينما كانت في بداية السطر متبوعة بنقطتين :
            pattern = r'(?i)(?:^|[^a-zA-Z])' + re.escape(key) + r'\s*:\s*(.*)'
            match = re.search(pattern, clean_line)
            if match:
                current_key = key
                value = match.group(1).strip()
                if value:
                    data[current_key].append(value)
                found_key = True
                break
                
        if not found_key and current_key:
            # تنظيف علامات الماركداون والنجوم الزائدة من الأسطر الفرعية المضافة
            line_clean = re.sub(r'^\*\*|\*\*$|^###\s*|^-\s*|^\*\s*', '', clean_line).strip()
            if line_clean:
                data[current_key].append(line_clean)
                
    return {k: "\n".join(v).strip() for k, v in data.items()}

# ========================================================
# 2. هندسة الأوامر (Prompts)
# ========================================================

def make_content_idea_post(items):
    if not items:
        return None
    titles = "\n".join([x["title"] + ": " + x["summary"][:200] for x in items[:15]])
    
    prompt = (
        "أنت المخرج الإبداعي وخبير السوشيال ميديا الأول في صناعة وفيديوهات الذكاء الاصطناعي التوليدي.\n"
        "إليك ملخص مقالات وتوجهات وفيديوهات الـ AI الصاعدة اليوم عالمياً:\n"
        + titles + "\n\n"
        "تعليمات صارمة:\n"
        "1. تجاهل أي أخبار عامة وركز 100% على (طرق صناعة المحتوى، الفيديوهات التوليدية، الخدع البصرية، الدمج بين الأدوات).\n"
        "2. ابتكر ووسع فكرة فيديو بشكل كامل ودسم.\n\n"
        "يجب أن تبدأ كل فقرة بالكلمة الإنجليزية المحددة تماماً كالتالي:\n"
        "IDEA: عنوان ملهم ومبتكر لفكرة فيديو قصير (Reel/TikTok/Short)\n"
        "WHY: تحليل دسم وعميق يوضح لماذا هذه الفكرة ستضرب ترند اليوم\n"
        "STEPS: دليل عملي (خطوة بخطوة) يشرح للمتابع كيف يصنع هذا الفيديو بالأدوات\n"
        "HOOK: اكتب 3 خيارات لجمل افتتاحية خطافية قوية لجذب المشاهد"
    )
    result = ask_ai(prompt)
    if not result:
        return None

    parsed = parse_ai_response(result, ["IDEA", "WHY", "STEPS", "HOOK"])
    if not parsed["IDEA"]:
        print("--- DEBUG: Idea Post Parsing Failed. Raw AI output was: ---")
        print(result)
        print("---------------------------------------------------------")
        return None

    return (
        "🎬 <b>رادار الترند وفكرة محتوى اليوم</b>\n"
        "🔥 <b>" + parsed["IDEA"] + "</b>\n\n"
        + "📈 <b>لماذا هذا الترند قوي جداً؟</b>\n" + parsed["WHY"] + "\n\n"
        + "🛠️ <b>دليل الحرفيين (كيف تصنع الفيديو):</b>\n" + parsed["STEPS"] + "\n\n"
        + "🎣 <b>جمل خطافية لإمساك المشاهد:</b>\n"
        + parsed["HOOK"] + "\n\n"
        + "#صناعة_محتوى #AIVideo #تيك_توك #صناع_المحتوى"
    )

def make_prompt_post(items):
    if not items:
        return None
    titles = "\n".join([x["title"] + ": " + x["summary"][:200] for x in items[:15]])
    
    prompt = (
        "أنت مهندس أوامر (Prompt Engineer) وفنان رقمي محترف متخصص في أدوات الصور.\n"
        "إليك أحدث المنشورات والنماذج الرائجة من مجتمعات التصميم الفني العالمية:\n"
        + titles + "\n\n"
        "تعليمات صارمة:\n"
        "1. استخلص 'لغة تصميم أو ستايل فني ساخن جداً' ومطلوب في السوشيال ميديا الآن.\n"
        "2. ابتكر برومبت إنجليزي طويل، دقيق، احترافي جاهز للنسخ.\n\n"
        "يجب أن تبدأ كل فقرة بالكلمة الإنجليزية المحددة تماماً كالتالي:\n"
        "STYLE: اسم الستايل الفني الرائج اليوم\n"
        "USE: أفكار إبداعية لصناع المحتوى لاستغلال هذا الستايل\n"
        "PROMPT: البرومبت الإنجليزي (ضعه بالكامل في سطر واحد بدون فواصل)\n"
        "TIPS: نصائح سرية لتعديل الإعدادات للحصول على نتائج مبهرة"
    )
    result = ask_ai(prompt)
    if not result:
        return None

    parsed = parse_ai_response(result, ["STYLE", "USE", "PROMPT", "TIPS"])
    if not parsed["STYLE"]:
        print("--- DEBUG: Prompt Post Parsing Failed. Raw AI output was: ---")
        print(result)
        print("---------------------------------------------------------")
        return None

    return (
        "✨ <b>برومبت اليوم السحري</b>\n"
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
    titles = "\n".join([x["title"] + ": " + x["summary"][:150] for x in items[:10]])
    prompt = (
        "أنت مستشار تقني تبحث عن أدوات الذكاء الاصطناعي لرفع إنتاجية صناع المحتوى.\n"
        "إليك أحدث الأدوات:\n"
        + titles + "\n\n"
        "يجب أن تبدأ كل فقرة بالكلمة الإنجليزية المحددة تماماً كالتالي:\n"
        "NAME: اسم الأداة\n"
        "VALUE: كيف تختصر هذه الأداة الوقت على صانع المحتوى؟\n"
        "USE_CASE: سيناريو عملي لكيفية استخدامها\n"
        "FOR: من هي الفئة المستفيدة"
    )
    result = ask_ai(prompt)
    if not result:
        return None

    parsed = parse_ai_response(result, ["NAME", "VALUE", "USE_CASE", "FOR"])
    if not parsed["NAME"]:
        print("--- DEBUG: Tool Post Parsing Failed. Raw AI output was: ---")
        print(result)
        print("---------------------------------------------------------")
        return None

    return (
        "🛠️ <b>ترسانة الكرييتورز | أداة اليوم 🤖</b>\n\n"
        + "⭐ <b>" + parsed["NAME"] + "</b>\n\n"
        + "⚡ <b>السحر والإنتاجية (كيف تختصر وقتك؟):</b>\n" + parsed["VALUE"] + "\n\n"
        + "🎯 <b>تطبيق سيناريو عملي:</b>\n" + parsed["USE_CASE"] + "\n\n"
        + "👥 <b>من يحتاج هذه الأداة فوراً؟</b>\n" + parsed["FOR"] + "\n\n"
        + "#أدوات_المحتوى #إنتاجية #صناع_المحتوى"
    )

# ========================================================
# 3. دالة التشغيل
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

    article_items = fetch_feed(SOURCES["ARTICLES"], max_per_feed=10)
    reddit_items = fetch_feed(SOURCES["REDDIT_COMMUNITIES"], max_per_feed=15)
    github_items = fetch_github_creative_trending(max_items=15)
    tool_items = fetch_feed(SOURCES["TOOLS"], max_per_feed=15)
    
    content_pool = article_items + github_items + reddit_items
    random.shuffle(content_pool)
    
    prompt_pool = reddit_items + article_items
    random.shuffle(prompt_pool)

    print(f"Data Pools loaded successfully. Content: {len(content_pool)}, Prompts: {len(prompt_pool)}")

    # 1. إرسال منشور فكرة محتوى الفيديو
    send_telegram("🎬 <b>رادار الترند وأفكار الفيديوهات القصيرة</b>\n━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")
    time.sleep(2)
    post = make_content_idea_post(content_pool)
    if post:
        send_telegram(post)
        print("Success: Generated Elite Content Idea Post")
    else:
        print("Failed to parse Idea Post")
    time.sleep(8)

    # 2. إرسال منشور البرومبت
    send_telegram("✨ <b>إلهام التصميم الرقمي وهندسة الأوامر</b>\n━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")
    time.sleep(2)
    post = make_prompt_post(prompt_pool)
    if post:
        send_telegram(post)
        print("Success: Generated Long Prompt Post")
    else:
         print("Failed to parse Prompt Post")
    time.sleep(8)

    # 3. إرسال أداة الإنتاجية
    send_telegram("🛠️ <b>أسلحة الكرييتورز (أدوات صناعة الميديا)</b>\n━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")
    time.sleep(2)
    post = make_creator_tool_post(tool_items)
    if post:
        send_telegram(post)
        print("Success: Generated Creator Tool Post")
    else:
         print("Failed to parse Tool Post")
    time.sleep(5)

    footer = (
        "✅ <b>جرعة الإلهام اليومية اكتملت بنجاح</b>\n"
        "المصادر غنية ومحدثة تلقائياً. حان الوقت لتبهر جمهورك؛ ابدأ بصناعة محتواك الآن! 🚀"
    )
    send_telegram(footer)
    print("Execution Finished Smoothly.")

if __name__ == "__main__":
    main()
