import feedparser
import requests
import re
import time
import os
from datetime import datetime

BOT_TOKEN = os.environ.get("BOT_TOKEN", "")
CHAT_ID = os.environ.get("CHAT_ID", "")
OPENROUTER_KEY = os.environ.get("OPENROUTER_KEY", "")

OPENROUTER_URL = "https://openrouter.ai/api/v1/chat/completions"
MODEL = "qwen/qwen-2.5-72b-instruct:free"

SOURCES = {
    "AI_NEWS": [
        "https://techcrunch.com/category/artificial-intelligence/feed/",
        "https://venturebeat.com/category/ai/feed/",
        "https://www.theverge.com/rss/ai-artificial-intelligence/index.xml",
        "https://www.technologyreview.com/feed/",
    ],
    "TRENDING": [
        "https://www.reddit.com/r/ChatGPT/top/.rss?t=day",
        "https://www.reddit.com/r/artificial/top/.rss?t=day",
        "https://www.reddit.com/r/LocalLLaMA/top/.rss?t=day",
    ],
    "TOOLS": [
        "https://www.producthunt.com/feed",
    ],
}


def fetch_feed(urls, max_per_feed=3):
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


def ask_ai(prompt):
    try:
        headers = {
            "Authorization": "Bearer " + OPENROUTER_KEY,
            "Content-Type": "application/json",
        }
        payload = {
            "model": MODEL,
            "messages": [{"role": "user", "content": prompt}],
            "max_tokens": 500,
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


def make_news_post(item):
    prompt = (
        "أنت محرر أخبار عربي متخصص في الذكاء الاصطناعي والتقنية.\n"
        "الخبر:\nالعنوان: " + item["title"] + "\nالتفاصيل: " + item["summary"] + "\n\n"
        "اكتب بالفصحى المبسطة فقط:\n"
        "TITLE: عنوان جذاب بالعربية\n"
        "SUMMARY: ملخص الخبر في جملتين\n"
        "WHY: لماذا يهم المستخدم العربي في جملة واحدة\n"
        "QUESTION: سؤال للجمهور يشجع على التفاعل"
    )
    result = ask_ai(prompt)
    if not result:
        return None

    title = summary = why = question = ""
    for line in result.splitlines():
        if line.startswith("TITLE:"):
            title = line.replace("TITLE:", "").strip()
        elif line.startswith("SUMMARY:"):
            summary = line.replace("SUMMARY:", "").strip()
        elif line.startswith("WHY:"):
            why = line.replace("WHY:", "").strip()
        elif line.startswith("QUESTION:"):
            question = line.replace("QUESTION:", "").strip()

    if not title:
        return None

    return (
        "📌 <b>" + title + "</b>\n\n"
        + summary + "\n\n"
        + "⚡️ " + why + "\n\n"
        + "💬 " + question + "\n\n"
        + "🔗 " + item["link"] + "\n\n"
        + "#ذكاء_اصطناعي #AI #تقنية"
    )


def make_trending_post(items):
    if not items:
        return None
    titles = "\n".join([x["title"] + ": " + x["summary"][:100] for x in items[:5]])
    prompt = (
        "أنت متخصص في الذكاء الاصطناعي.\n"
        "هذه المواضيع الأكثر تداولاً اليوم على Reddit في مجال AI:\n"
        + titles + "\n\n"
        "اكتب بالفصحى المبسطة:\n"
        "TITLE: عنوان جذاب عن أبرز ترند اليوم\n"
        "TREND: ما الذي يتحدث عنه الناس في عالم AI اليوم في 3 جمل\n"
        "PROMPT: برومبت عملي مستوحى من هذا الترند جاهز للنسخ\n"
        "QUESTION: سؤال للجمهور"
    )
    result = ask_ai(prompt)
    if not result:
        return None

    title = trend = prompt_text = question = ""
    for line in result.splitlines():
        if line.startswith("TITLE:"):
            title = line.replace("TITLE:", "").strip()
        elif line.startswith("TREND:"):
            trend = line.replace("TREND:", "").strip()
        elif line.startswith("PROMPT:"):
            prompt_text = line.replace("PROMPT:", "").strip()
        elif line.startswith("QUESTION:"):
            question = line.replace("QUESTION:", "").strip()

    if not title:
        return None

    return (
        "🔥 <b>ترند اليوم | " + title + "</b>\n\n"
        + "📊 " + trend + "\n\n"
        + "🧠 <b>برومبت اليوم:</b>\n"
        + "<code>" + prompt_text + "</code>\n\n"
        + "💬 " + question + "\n\n"
        + "#ترند #ذكاء_اصطناعي #AI"
    )


def make_tool_post(items):
    if not items:
        return None
    titles = "\n".join([x["title"] + ": " + x["summary"][:150] for x in items[:5]])
    prompt = (
        "أنت خبير في أدوات الذكاء الاصطناعي.\n"
        "هذه أحدث الأدوات على ProductHunt اليوم:\n"
        + titles + "\n\n"
        "اختر الأداة الأكثر فائدة للمستخدم العربي واكتب بالفصحى المبسطة:\n"
        "NAME: اسم الأداة\n"
        "USE: ما تستخدم فيه في جملة واحدة\n"
        "HOW: كيف تبدأ معها في جملتين\n"
        "FOR: من يستفيد منها أكثر"
    )
    result = ask_ai(prompt)
    if not result:
        return None

    name = use = how = for_who = ""
    for line in result.splitlines():
        if line.startswith("NAME:"):
            name = line.replace("NAME:", "").strip()
        elif line.startswith("USE:"):
            use = line.replace("USE:", "").strip()
        elif line.startswith("HOW:"):
            how = line.replace("HOW:", "").strip()
        elif line.startswith("FOR:"):
            for_who = line.replace("FOR:", "").strip()

    if not name:
        return None

    return (
        "🛠️ <b>أداة اليوم 🤖</b>\n\n"
        + "⭐ <b>" + name + "</b>\n\n"
        + "🎯 " + use + "\n\n"
        + "💡 " + how + "\n\n"
        + "👥 " + for_who + "\n\n"
        + "#أدوات_AI #ProductHunt #ذكاء_اصطناعي"
    )


def main():
    today = datetime.now().strftime("%Y/%m/%d")
    print("Starting - " + today)

    header = (
        "🤖 <b>ملخص الذكاء الاصطناعي والتقنية</b>\n"
        "📅 " + today + "\n"
        "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
        "ترند • أدوات • أخبار"
    )
    send_telegram(header)
    time.sleep(2)

    ai_items = fetch_feed(SOURCES["AI_NEWS"], max_per_feed=3)
    trending_items = fetch_feed(SOURCES["TRENDING"], max_per_feed=3)
    tool_items = fetch_feed(SOURCES["TOOLS"], max_per_feed=5)

    print("AI: " + str(len(ai_items)) + " | Trending: " + str(len(trending_items)) + " | Tools: " + str(len(tool_items)))

    # 1. ترند اليوم + برومبت
    send_telegram("🔥 <b>ترند اليوم</b>\n━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")
    time.sleep(1)
    post = make_trending_post(trending_items)
    if post:
        send_telegram(post)
        print("OK: trending")
    time.sleep(5)

    # 2. أداة اليوم
    send_telegram("🛠️ <b>أداة اليوم</b>\n━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")
    time.sleep(1)
    post = make_tool_post(tool_items)
    if post:
        send_telegram(post)
        print("OK: tool")
    time.sleep(5)

    # 3. أبرز أخبار AI
    send_telegram("📰 <b>أبرز أخبار AI</b>\n━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")
    time.sleep(1)
    for item in ai_items[:3]:
        post = make_news_post(item)
        if post:
            send_telegram(post)
            print("OK: " + item["title"][:50])
        time.sleep(5)

    footer = (
        "✅ <b>انتهى ملخص اليوم</b>\n"
        "خذ ما يناسبك، أضف صوتك، انشر 💪"
    )
    send_telegram(footer)
    print("Done")


if __name__ == "__main__":
    main()
