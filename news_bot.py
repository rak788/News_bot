import feedparser
import requests
import re
import time
import os
from datetime import datetime, timedelta
import random

BOT_TOKEN = os.environ.get("BOT_TOKEN", "")
CHAT_ID = os.environ.get("CHAT_ID", "")
OPENROUTER_KEY = os.environ.get("OPENROUTER_KEY", "")

OPENROUTER_URL = "https://openrouter.ai/api/v1/chat/completions"
MODEL = "openai/gpt-oss-120b:free"

# تم إزالة أداة alexi والاعتماد على المصادر الرسمية فقط
SOURCES = {
    "AI_NEWS": [
        "https://techcrunch.com/category/artificial-intelligence/feed/",
        "https://venturebeat.com/category/ai/feed/",
        "https://www.theverge.com/rss/ai-artificial-intelligence/index.xml",
        "https://www.technologyreview.com/feed/",
        "https://www.wired.com/feed/category/ai/latest/rss",
    ],
    "TRENDING_REDDIT": [
        "https://www.reddit.com/r/ChatGPT/top/.rss?t=day",
        "https://www.reddit.com/r/LocalLLaMA/top/.rss?t=day",
        "https://www.reddit.com/r/OpenAI/top/.rss?t=day",
        "https://www.reddit.com/r/singularity/top/.rss?t=day",
    ],
    "TOOLS": [
        "https://www.producthunt.com/feed",
        "https://hnrss.org/newest?q=AI",
    ],
}


def fetch_feed(urls, max_per_feed=5):
    items = []
    for url in urls:
        try:
            headers = {"User-Agent": "Mozilla/5.0 (compatible; NewsBot/1.0)"}
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


# دالة جديدة كلياً لجلب ترندات الذكاء الاصطناعي من GitHub API الرسمي
def fetch_github_trending(max_items=5):
    items = []
    try:
        # جلب المشاريع المستودعة التي تم إنشاؤها أو تحديثها وتخص الذكاء الاصطناعي بلغة بايثون
        # ومفرزة بحسب عدد النجوم المستلمة مؤخراً لضمان أنها "ترند"
        headers = {"User-Agent": "Mozilla/5.0 (compatible; NewsBot/1.0)"}
        url = "https://api.github.com/search/repositories?q=topic:ai+language:python&sort=stars&order=desc&per_page=10"
        
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


def make_news_post(item):
    prompt = (
        "أنت محرر أخبار عربي متخصص ومحترف في الذكاء الاصطناعي.\n"
        "الخبر:\nالعنوان: " + item["title"] + "\nالتفاصيل: " + item["summary"] + "\n\n"
        "اكتب بالفصحى المبسطة فقط وبدون مقدمات:\n"
        "TITLE: عنوان جذاب وقوي بالعربية\n"
        "SUMMARY: ملخص وافٍ للخبر يشرح التفاصيل المهمة (3-4 جمل)\n"
        "WHY: تحليل موجز: لماذا هذا الخبر مهم لمستقبل التقنية؟\n"
        "QUESTION: سؤال عميق للجمهور يشجع على النقاش"
    )
    result = ask_ai(prompt)
    if not result:
        return None

    parsed = parse_ai_response(result, ["TITLE", "SUMMARY", "WHY", "QUESTION"])
    if not parsed["TITLE"]:
        return None

    return (
        "📌 <b>" + parsed["TITLE"] + "</b>\n\n"
        + parsed["SUMMARY"] + "\n\n"
        + "⚡️ <b>الأهمية:</b> " + parsed["WHY"] + "\n\n"
        + "💬 " + parsed["QUESTION"] + "\n\n"
        + "🔗 " + item["link"] + "\n\n"
        + "#أخبار_تقنية #ذكاء_اصطناعي #AI"
    )


def make_trending_post(items):
    if not items:
        return None
    titles = "\n".join([x["title"] + ": " + x["summary"][:150] for x in items[:15]])
    prompt = (
        "أنت محلل تقني خبير تدمج بين نقاشات المجتمعات والمشاريع البرمجية المفتوحة.\n"
        "إليك مزيج من المنشورات الأكثر تفاعلاً على Reddit والمشاريع البرمجية الأكثر صعوداً على موقع GitHub الرسمي اليوم:\n"
        + titles + "\n\n"
        "استخرج القاسم المشترك أو أبرز توجه تقني (ترند) يركز عليه المطورون والمستخدمون الآن، واكتب بالفصحى وبدون مقدمات:\n"
        "TITLE: عنوان مثير يجمع بين توجهات مجتمعات Reddit ومشاريع GitHub الساخنة\n"
        "TREND: تحليل دسم وعميق للترند (كيف يتفاعل معه الناس في رديت وما هي نوعية المشاريع التي يتم بناؤها على جيتهاب حوله حالياً؟)\n"
        "PROMPT: اكتب برومبت (Prompt) احترافي، متطور، وطويل مستوحى من هذا الترند لكي يستفيد منه المستخدم عادي أو المطور في نماذج الذكاء الاصطناعي\n"
        "QUESTION: سؤال تفاعلي ذكي للجمهور"
    )
    result = ask_ai(prompt)
    if not result:
        return None

    parsed = parse_ai_response(result, ["TITLE", "TREND", "PROMPT", "QUESTION"])
    if not parsed["TITLE"]:
        return None

    return (
        "🔥 <b>ترند اليوم | رديت &amp; جيتهاب</b>\n"
        "عنوان الترند: <b>" + parsed["TITLE"] + "</b>\n\n"
        + "📊 <b>التحليل التقني للساحة:</b>\n" + parsed["TREND"] + "\n\n"
        + "🧠 <b>برومبت اليوم الاحترافي (انسخ وجرب):</b>\n"
        + "<code>" + parsed["PROMPT"] + "</code>\n\n"
        + "💬 " + parsed["QUESTION"] + "\n\n"
        + "#ترند_التقنية #GitHub #Reddit #ذكاء_اصطناعي"
    )


def make_tool_post(items):
    if not items:
        return None
    titles = "\n".join([x["title"] + ": " + x["summary"][:150] for x in items[:10]])
    prompt = (
        "أنت خبير تقني تراجع أدوات الذكاء الاصطناعي.\n"
        "هذه أحدث الأدوات التقنية اليوم:\n"
        + titles + "\n\n"
        "اختر الأداة الأكثر ابتكاراً والمفيدة للمستخدم العربي واكتب بالفصحى وبدون مقدمات:\n"
        "NAME: اسم الأداة\n"
        "USE: شرح مفصل لمميزاتها وكيف تحل مشكلة للمستخدم\n"
        "HOW: خطوات بسيطة لكيفية البدء في استخدامها\n"
        "FOR: من هو الجمهور المستفيد منها بشكل أساسي"
    )
    result = ask_ai(prompt)
    if not result:
        return None

    parsed = parse_ai_response(result, ["NAME", "USE", "HOW", "FOR"])
    if not parsed["NAME"]:
        return None

    return (
        "🛠️ <b>أداة اليوم 🤖</b>\n\n"
        + "⭐ <b>" + parsed["NAME"] + "</b>\n\n"
        + "🎯 <b>ماذا تفعل؟</b>\n" + parsed["USE"] + "\n\n"
        + "💡 <b>كيف تبدأ؟</b>\n" + parsed["HOW"] + "\n\n"
        + "👥 <b>لمن هذه الأداة؟</b>\n" + parsed["FOR"] + "\n\n"
        + "#أدوات_AI #إنتاجية #ذكاء_اصطناعي"
    )


def main():
    today = datetime.now().strftime("%Y/%m/%d")
    print("Starting - " + today)

    header = (
        "🤖 <b>النشرة التقنية الشاملة للذكاء الاصطناعي</b>\n"
        "📅 " + today + "\n"
        "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
        "🔥 ترند • 🛠️ أدوات • 📰 أخبار"
    )
    send_telegram(header)
    time.sleep(2)

    # جلب البيانات من المصادر الرسمية فقط
    ai_items = fetch_feed(SOURCES["AI_NEWS"], max_per_feed=5)
    reddit_items = fetch_feed(SOURCES["TRENDING_REDDIT"], max_per_feed=4)
    github_items = fetch_github_trending(max_items=5) # استدعاء الدالة الرسمية والآمنة لـ GitHub
    tool_items = fetch_feed(SOURCES["TOOLS"], max_per_feed=5)
    
    # دمج ترندات رديت مع ترندات جيتهاب الرسمية في قائمة واحدة للترند
    trending_combined = reddit_items + github_items
    random.shuffle(trending_combined)
    
    random.shuffle(ai_items)

    print("AI: " + str(len(ai_items)) + " | Trending (Combined): " + str(len(trending_combined)) + " | Tools: " + str(len(tool_items)))

    # 1. ترند اليوم المشترك (Reddit + GitHub الرسمي) + برومبت
    send_telegram("🔥 <b>ترند ومجتمعات AI (رديت &amp; جيتهاب الرسمي)</b>\n━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")
    time.sleep(1)
    post = make_trending_post(trending_combined)
    if post:
        send_telegram(post)
        print("OK: trending")
    time.sleep(5)

    # 2. أداة اليوم
    send_telegram("🛠️ <b>اكتشافات وأدوات</b>\n━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")
    time.sleep(1)
    post = make_tool_post(tool_items)
    if post:
        send_telegram(post)
        print("OK: tool")
    time.sleep(5)

    # 3. أبرز أخبار AI
    send_telegram("📰 <b>أهم الأخبار التقنية</b>\n━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")
    time.sleep(1)
    for item in ai_items[:5]:
        post = make_news_post(item)
        if post:
            send_telegram(post)
            print("OK: " + item["title"][:50])
        time.sleep(5)

    footer = (
        "✅ <b>نهاية نشرة اليوم</b>\n"
        "لا تنسَ مشاركة النشرة مع المهتمين بالتقنية 🚀"
    )
    send_telegram(footer)
    print("Done")


if __name__ == "__main__":
    main()
