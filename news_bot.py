import feedparser
import requests
import re
import time
import os
from google import genai
from datetime import datetime

BOT_TOKEN = os.environ.get("BOT_TOKEN", "")
CHAT_ID = os.environ.get("CHAT_ID", "")
GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY", "")

client = genai.Client(api_key=GEMINI_API_KEY)

# === المصادر ===
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
        "https://www.reddit.com/r/MachineLearning/top/.rss?t=day",
        "https://www.reddit.com/r/LocalLLaMA/top/.rss?t=day",
    ],
    "TOOLS": [
        "https://www.producthunt.com/feed",
        "https://www.reddit.com/r/ChatGPT/search.rss?q=prompt&sort=top&t=day",
    ],
    "GITHUB": [
        "https://github.com/trending/python?since=daily&spoken_language_code=en",
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


def fetch_github_trending():
    try:
        headers = {"User-Agent": "Mozilla/5.0"}
        r = requests.get("https://github.com/trending?since=daily", headers=headers, timeout=10)
        items = []
        matches = re.findall(r'href="/([^/]+/[^"]+)"[^>]*class="[^"]*Link[^"]*"', r.text)
        for m in matches[:5]:
            items.append({
                "title": m,
                "summary": "Trending repository on GitHub today",
                "link": "https://github.com/" + m
            })
        return items
    except Exception as e:
        print("GitHub error: " + str(e))
        return []


def ask_gemini(prompt):
    try:
        response = client.models.generate_content(model="gemini-2.0-flash", contents=prompt)
        return response.text.strip()
    except Exception as e:
        print("Gemini error: " + str(e))
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
        "أنت متخصص في الذكاء الاصطناعي وصانع محتوى عربي محترف.\n"
        "الخبر:\nالعنوان: " + item["title"] + "\nالتفاصيل: " + item["summary"] + "\n\n"
        "اكتب بالفصحى المبسطة:\n"
        "TITLE: عنوان جذاب بالعربية\n"
        "SUMMARY: ملخص في جملتين\n"
        "WHY: لماذا يهم المستخدم العربي (جملة واحدة)\n"
        "QUESTION: سؤال للجمهور يشجع التفاعل"
    )
    result = ask_gemini(prompt)
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
        "\U0001f4cc <b>" + title + "</b>\n\n"
        + summary + "\n\n"
        + "\u26a1\ufe0f " + why + "\n\n"
        + "\U0001f4ac " + question + "\n\n"
        + "\U0001f517 " + item["link"] + "\n\n"
        + "#\u0630\u0643\u0627\u0621_\u0627\u0635\u0637\u0646\u0627\u0639\u064a #AI #\u062a\u0642\u0646\u064a\u0629"
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
        "TREND: ما الذي يتحدث عنه الناس اليوم في عالم AI (3 جمل)\n"
        "PROMPT: اقترح برومبت عملي مستوحى من هذا الترند، جاهز للنسخ\n"
        "QUESTION: سؤال للجمهور"
    )
    result = ask_gemini(prompt)
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
        "\U0001f525 <b>\u062a\u0631\u0646\u062f \u0627\u0644\u064a\u0648\u0645 | " + title + "</b>\n\n"
        + "\U0001f4ca " + trend + "\n\n"
        + "\U0001f9e0 <b>\u0628\u0631\u0648\u0645\u0628\u062a \u0645\u0633\u062a\u0648\u062d\u0649 \u0645\u0646 \u0627\u0644\u062a\u0631\u0646\u062f:</b>\n"
        + "<code>" + prompt_text + "</code>\n\n"
        + "\U0001f4ac " + question + "\n\n"
        + "#\u062a\u0631\u0646\u062f #\u0630\u0643\u0627\u0621_\u0627\u0635\u0637\u0646\u0627\u0639\u064a #Reddit #AI"
    )


def make_tool_post(items):
    if not items:
        return None
    titles = "\n".join([x["title"] + ": " + x["summary"][:150] for x in items[:4]])
    prompt = (
        "أنت خبير في أدوات الذكاء الاصطناعي.\n"
        "هذه أحدث الأدوات على ProductHunt اليوم:\n"
        + titles + "\n\n"
        "اختر الأداة الأكثر فائدة للمستخدم العربي واكتب بالفصحى المبسطة:\n"
        "NAME: اسم الأداة\n"
        "USE: ما تستخدم فيه (جملة واحدة)\n"
        "HOW: كيف تبدأ معها (جملتان)\n"
        "FOR: من يستفيد منها أكثر\n"
        "LINK: رابط الأداة من القائمة أعلاه"
    )
    result = ask_gemini(prompt)
    if not result:
        return None

    name = use = how = for_who = link = ""
    for line in result.splitlines():
        if line.startswith("NAME:"):
            name = line.replace("NAME:", "").strip()
        elif line.startswith("USE:"):
            use = line.replace("USE:", "").strip()
        elif line.startswith("HOW:"):
            how = line.replace("HOW:", "").strip()
        elif line.startswith("FOR:"):
            for_who = line.replace("FOR:", "").strip()
        elif line.startswith("LINK:"):
            link = line.replace("LINK:", "").strip()

    if not name:
        return None

    return (
        "\U0001f6e0\ufe0f <b>\u0623\u062f\u0627\u0629 \u0627\u0644\u064a\u0648\u0645 \U0001f916</b>\n\n"
        + "\u2b50 <b>" + name + "</b>\n\n"
        + "\U0001f3af " + use + "\n\n"
        + "\U0001f4a1 " + how + "\n\n"
        + "\U0001f465 " + for_who + "\n\n"
        + ("\U0001f517 " + link + "\n\n" if link else "")
        + "#\u0623\u062f\u0648\u0627\u062a_AI #ProductHunt #\u0630\u0643\u0627\u0621_\u0627\u0635\u0637\u0646\u0627\u0639\u064a"
    )


def make_github_post(items):
    if not items:
        return None
    repos = "\n".join([x["title"] for x in items[:5]])
    prompt = (
        "أنت مطور ومتخصص في الذكاء الاصطناعي.\n"
        "هذه أكثر المشاريع انتشاراً على GitHub اليوم:\n"
        + repos + "\n\n"
        "اختر المشروع الأكثر فائدة واكتب بالفصحى المبسطة:\n"
        "TITLE: عنوان جذاب\n"
        "WHAT: ما هذا المشروع (جملتان)\n"
        "WHY: لماذا يهم مجتمع AI العربي\n"
        "QUESTION: سؤال للمطورين"
    )
    result = ask_gemini(prompt)
    if not result:
        return None

    title = what = why = question = ""
    repo_link = ""
    for line in result.splitlines():
        if line.startswith("TITLE:"):
            title = line.replace("TITLE:", "").strip()
        elif line.startswith("WHAT:"):
            what = line.replace("WHAT:", "").strip()
        elif line.startswith("WHY:"):
            why = line.replace("WHY:", "").strip()
        elif line.startswith("QUESTION:"):
            question = line.replace("QUESTION:", "").strip()

    if items:
        repo_link = items[0]["link"]

    if not title:
        return None

    return (
        "\U0001f4bb <b>GitHub Trending | " + title + "</b>\n\n"
        + "\U0001f527 " + what + "\n\n"
        + "\U0001f31f " + why + "\n\n"
        + "\U0001f4ac " + question + "\n\n"
        + "\U0001f517 " + repo_link + "\n\n"
        + "#GitHub #\u0645\u0637\u0648\u0631\u064a\u0646 #\u0630\u0643\u0627\u0621_\u0627\u0635\u0637\u0646\u0627\u0639\u064a #OpenSource"
    )


def main():
    today = datetime.now().strftime("%Y/%m/%d")
    print("Starting - " + today)

    header = (
        "\U0001f916 <b>\u0645\u0644\u062e\u0635 \u0627\u0644\u0630\u0643\u0627\u0621 \u0627\u0644\u0627\u0635\u0637\u0646\u0627\u0639\u064a \u0648\u0627\u0644\u062a\u0642\u0646\u064a\u0629</b>\n"
        "\U0001f4c5 " + today + "\n"
        "\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\n"
        "\u062a\u0631\u0646\u062f \u2022 \u0623\u062f\u0648\u0627\u062a \u2022 \u0623\u062e\u0628\u0627\u0631 \u2022 GitHub"
    )
    send_telegram(header)
    time.sleep(2)

    # جلب كل المصادر
    ai_items = fetch_feed(SOURCES["AI_NEWS"], max_per_feed=3)
    trending_items = fetch_feed(SOURCES["TRENDING"], max_per_feed=3)
    tool_items = fetch_feed(SOURCES["TOOLS"], max_per_feed=4)
    github_items = fetch_github_trending()

    print("AI: " + str(len(ai_items)) + " | Trending: " + str(len(trending_items)) +
          " | Tools: " + str(len(tool_items)) + " | GitHub: " + str(len(github_items)))

    # 1. ترند اليوم + برومبت مستوحى منه
    send_telegram("\U0001f525 <b>\u062a\u0631\u0646\u062f \u0627\u0644\u064a\u0648\u0645</b>\n\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501")
    time.sleep(1)
    post = make_trending_post(trending_items)
    if post:
        send_telegram(post)
        print("OK: trending")
    time.sleep(6)

    # 2. أداة اليوم من ProductHunt
    send_telegram("\U0001f6e0\ufe0f <b>\u0623\u062f\u0627\u0629 \u0627\u0644\u064a\u0648\u0645</b>\n\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501")
    time.sleep(1)
    post = make_tool_post(tool_items)
    if post:
        send_telegram(post)
        print("OK: tool")
    time.sleep(6)

    # 3. GitHub Trending
    send_telegram("\U0001f4bb <b>GitHub Trending</b>\n\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501")
    time.sleep(1)
    post = make_github_post(github_items)
    if post:
        send_telegram(post)
        print("OK: github")
    time.sleep(6)

    # 4. أبرز أخبار AI
    send_telegram("\U0001f4f0 <b>\u0623\u0628\u0631\u0632 \u0623\u062e\u0628\u0627\u0631 AI</b>\n\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501")
    time.sleep(1)
    for item in ai_items[:3]:
        post = make_news_post(item)
        if post:
            send_telegram(post)
            print("OK: " + item["title"][:50])
        time.sleep(6)

    footer = (
        "\u2705 <b>\u0627\u0646\u062a\u0647\u0649 \u0645\u0644\u062e\u0635 \u0627\u0644\u064a\u0648\u0645</b>\n"
        "\u062e\u0630 \u0645\u0627 \u064a\u0646\u0627\u0633\u0628\u0643\u060c \u0623\u0636\u0641 \u0635\u0648\u062a\u0643\u060c \u0627\u0646\u0634\u0631 \U0001f4aa"
    )
    send_telegram(footer)
    print("Done")


if __name__ == "__main__":
    main()
