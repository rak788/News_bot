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

SOURCES = {
    # مجتمعات البرومبتات والصور (Reddit + Civitai الرسمي)
    "PROMPTS": [
        "https://www.reddit.com/r/midjourney/top/.rss?t=day",
        "https://www.reddit.com/r/StableDiffusion/top/.rss?t=day",
        "https://www.reddit.com/r/PromptEngineering/top/.rss?t=day",
        "https://civitai.com/api/v1/feeds/models", # تم إضافة رابط Civitai الرسمي والآمن هنا لتقديم أحدث النماذج والبرومبتات
    ],
    # ترندات الفيديو وصناعة المحتوى (X/Twitter عبر RSSHub + YouTube + Reddit)
    "CONTENT_CREATION": [
        "https://www.reddit.com/r/aivideo/top/.rss?t=day",
        "https://www.youtube.com/feeds/videos.xml?channel_id=UCwOALC0U6D3L2k3vG_o_Tiw",
        "https://rsshub.app/twitter/keyword/AIVideo", 
        "https://rsshub.app/twitter/keyword/Midjourney",
    ],
    # الأدوات التقنية لصناع المحتوى
    "TOOLS": [
        "https://www.producthunt.com/feed",
    ],
}


def fetch_feed(urls, max_per_feed=5):
    items = []
    for url in urls:
        try:
            headers = {"User-Agent": "Mozilla/5.0 (compatible; CreatorBot/1.0)"}
            feed = feedparser.parse(url, request_headers=headers)
            for entry in feed.entries[:max_per_feed]:
                title = entry.get("title", "").strip()
                summary = entry.get("summary", entry.get("description", "")).strip()
                link = entry.get("link", "").strip()
                summary = re.sub(r'<[^>]+>', '', summary)[:400].strip()
                if title and link:
                    items.append({"title": title, "summary": summary, "link": link})
        except Exception as e:
            print("RSS error: " + str(e))
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
            "max_tokens": 900,
        }
        r = requests.post(OPENROUTER_URL, headers=headers, json=payload, timeout=30)
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


def make_prompt_post(items):
    if not items:
        return None
    titles = "\n".join([x["title"] + ": " + x["summary"][:150] for x in items[:12]])
    prompt = (
        "أنت فنان ومصمم محترف تستخدم أدوات توليد الصور (Midjourney, Stable Diffusion, Civitai).\n"
        "إليك أحدث الأفكار والنماذج والصور الرائجة اليوم من مجتمعات المصممين ومنصة Civitai:\n"
        + titles + "\n\n"
        "استخرج ستايل تصميم ترند اليوم، واكتب بالفصحى المبسطة وبدون مقدمات:\n"
        "STYLE: اسم الستايل أو فكرة التصميم الحالية الرائجة\n"
        "USE: كيف يمكن لصانع المحتوى الاستفادة من هذا الستايل لزيادة تفاعل حساباته؟\n"
        "PROMPT: اكتب برومبت (Prompt) إنجليزي احترافي، تفصيلي، ودقيق جداً جاهز للنسخ لتوليد صورة مذهلة بهذا الستايل\n"
        "TIPS: نصيحة واحدة سرية للمصممين حول كيفية تعديل هذا البرومبت أو الإعدادات للحصول على أفضل نتيجة"
    )
    result = ask_ai(prompt)
    if not result:
        return None

    parsed = parse_ai_response(result, ["STYLE", "USE", "PROMPT", "TIPS"])
    if not parsed["STYLE"]:
        return None

    return (
        "✨ <b>برومبت اليوم السحري (الهام من Reddit &amp; Civitai)</b>\n"
        "🎨 الستايل: <b>" + parsed["STYLE"] + "</b>\n\n"
        + "🎯 <b>استخداماته:</b>\n" + parsed["USE"] + "\n\n"
        + "🧠 <b>البرومبت (انسخ وجرب):</b>\n"
        + "<code>" + parsed["PROMPT"] + "</code>\n\n"
        + "💡 <b>نصيحة للمحترفين:</b>\n" + parsed["TIPS"] + "\n\n"
        + "#Midjourney #Civitai #تصميم #ذكاء_اصطناعي"
    )


def make_content_idea_post(items):
    if not items:
        return None
    titles = "\n".join([x["title"] + ": " + x["summary"][:150] for x in items[:10]])
    prompt = (
        "أنت خبير في السوشيال ميديا وصناعة الفيديوهات بالذكاء الاصطناعي.\n"
        "إليك أحدث الترندات من (X/تويتر)، (يوتيوب)، ومجتمع (AI Video):\n"
        + titles + "\n\n"
        "استنبط فكرة محتوى (فيديو قصير Reel/TikTok) قوية وترند يمكن للمتابع تنفيذها، واكتب بالفصحى وبدون مقدمات:\n"
        "IDEA: عنوان جذاب للفكرة (مثال: اصنع فيديو وثائقي خيالي بالذكاء الاصطناعي)\n"
        "WHY: لماذا هذه الفكرة ستجلب مشاهدات وتفاعل اليوم؟\n"
        "STEPS: خطوات العمل (الأدوات المستخدمة وكيفية ربطها ببعض لصناعة الفيديو)\n"
        "HOOK: اكتب 'جملة خطافية' (Hook) قوية يبدأ بها صانع المحتوى الفيديو الخاص به لجذب الانتباه"
    )
    result = ask_ai(prompt)
    if not result:
        return None

    parsed = parse_ai_response(result, ["IDEA", "WHY", "STEPS", "HOOK"])
    if not parsed["IDEA"]:
        return None

    return (
        "🎬 <b>فكرة محتوى وترند اليوم</b>\n"
        "🔥 <b>" + parsed["IDEA"] + "</b>\n\n"
        + "📈 <b>ليش الترند قوي؟</b>\n" + parsed["WHY"] + "\n\n"
        + "🛠️ <b>كيف تنفذ الفكرة خطوة بخطوة؟</b>\n" + parsed["STEPS"] + "\n\n"
        + "🎣 <b>جملة البداية (Hook) لفيدوك:</b>\n"
        + "«" + parsed["HOOK"] + "»\n\n"
        + "#صناعة_محتوى #AIVideo #Reels"
    )


def make_creator_tool_post(items):
    if not items:
        return None
    titles = "\n".join([x["title"] + ": " + x["summary"][:150] for x in items[:15]])
    prompt = (
        "أنت مخرج إبداعي تبحث عن أدوات الذكاء الاصطناعي لمساعدة فريقك.\n"
        "هذه أحدث الأدوات التقنية:\n"
        + titles + "\n\n"
        "اختر أداة واحدة فقط تفيد 'صناع المحتوى' (سواء للمونتاج، تعديل الصوت، كتابة السكربت، أو التصميم). تجاهل أدوات البرمجة المعقدة. واكتب بالفصحى:\n"
        "NAME: اسم الأداة\n"
        "VALUE: كيف ستختصر هذه الأداة الوقت على صانع المحتوى؟\n"
        "USE_CASE: مثال عملي لاستخدامها في فيديو أو بوست\n"
        "FOR: من يحتاجها (يوتيوبرز، صناع بودكاست، مصممين..)"
    )
    result = ask_ai(prompt)
    if not result:
        return None

    parsed = parse_ai_response(result, ["NAME", "VALUE", "USE_CASE", "FOR"])
    if not parsed["NAME"]:
        return None

    return (
        "🛠️ <b>أداة الكرييتورز اليوم</b>\n\n"
        + "⭐ <b>" + parsed["NAME"] + "</b>\n\n"
        + "⚡ <b>القيمة المضافة:</b>\n" + parsed["VALUE"] + "\n\n"
        + "🎯 <b>مثال عملي:</b>\n" + parsed["USE_CASE"] + "\n\n"
        + "👥 <b>لمن هذه الأداة؟</b>\n" + parsed["FOR"] + "\n\n"
        + "#أدوات_ذكية #إنتاجية #صناع_المحتوى"
    )


def main():
    today = datetime.now().strftime("%Y/%m/%d")
    print("Starting Creator Bot - " + today)

    header = (
        "🎨 <b>أكاديمية صناع المحتوى بالذكاء الاصطناعي</b>\n"
        "📅 " + today + "\n"
        "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
        "✨ برومبتات • 🎬 أفكار محتوى • 🛠️ أدوات"
    )
    send_telegram(header)
    time.sleep(2)

    prompt_items = fetch_feed(SOURCES["PROMPTS"], max_per_feed=5)
    content_items = fetch_feed(SOURCES["CONTENT_CREATION"], max_per_feed=5)
    tool_items = fetch_feed(SOURCES["TOOLS"], max_per_feed=10)
    
    random.shuffle(prompt_items)
    random.shuffle(content_items)

    print("Prompts (inc. Civitai): " + str(len(prompt_items)) + " | Content Ideas: " + str(len(content_items)) + " | Tools: " + str(len(tool_items)))

    # 1. فكرة المحتوى والفيديو
    send_telegram("🎬 <b>رادار الترند وأفكار الفيديوهات</b>\n━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")
    time.sleep(1)
    post = make_content_idea_post(content_items)
    if post:
        send_telegram(post)
        print("OK: Content Idea")
    time.sleep(5)

    # 2. برومبت التصميم السحري (يدعم Civitai حالياً)
    send_telegram("✨ <b>إلهام التصميم وهندسة الأوامر</b>\n━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")
    time.sleep(1)
    post = make_prompt_post(prompt_items)
    if post:
        send_telegram(post)
        print("OK: Prompt")
    time.sleep(5)

    # 3. أداة اليوم لصناع المحتوى
    send_telegram("🛠️ <b>أسلحة الكرييتورز (أدوات)</b>\n━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")
    time.sleep(1)
    post = make_creator_tool_post(tool_items)
    if post:
        send_telegram(post)
        print("OK: Tool")
    time.sleep(5)

    footer = (
        "✅ <b>جرعة الإلهام اليومية اكتملت</b>\n"
        "ابدأ صناعة محتواك الآن، ولا تنسَ مشاركة النشرة 🚀"
    )
    send_telegram(footer)
    print("Done")


if __name__ == "__main__":
    main()
