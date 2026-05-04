import feedparser
import requests
import re
import time
import os
import google.generativeai as genai
from datetime import datetime

BOT_TOKEN = os.environ.get("BOT_TOKEN", "")
CHAT_ID = os.environ.get("CHAT_ID", "")
GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY", "")

genai.configure(api_key=GEMINI_API_KEY)
model = genai.GenerativeModel("gemini-2.0-flash")

RSS_FEEDS = {
    "Finance": [
        "https://feeds.reuters.com/reuters/businessNews",
        "https://feeds.reuters.com/reuters/companyNews",
        "https://www.cnbc.com/id/10000664/device/rss/rss.html",
    ],
    "Business": [
        "https://feeds.reuters.com/reuters/topNews",
        "https://www.cnbc.com/id/10001147/device/rss/rss.html",
    ],
    "AI": [
        "https://techcrunch.com/category/artificial-intelligence/feed/",
        "https://venturebeat.com/category/ai/feed/",
        "https://www.technologyreview.com/feed/",
    ],
    "Tech": [
        "https://www.theverge.com/rss/index.xml",
        "https://feeds.arstechnica.com/arstechnica/technology-lab",
        "https://www.wired.com/feed/rss",
    ],
    "Arabic": [
        "https://www.aljazeera.net/xmlfeeds/rss2.0.xml?section=business",
        "https://arabic.rt.com/rss/economy/",
    ],
}

CATEGORY_LABELS = {
    "Finance":  "\u0645\u0627\u0644 \u0648\u0623\u0633\u0648\u0627\u0642 \U0001f4b0",
    "Business": "\u0623\u0639\u0645\u0627\u0644 \u0648\u0634\u0631\u0643\u0627\u062a \U0001f3e2",
    "AI":       "\u0630\u0643\u0627\u0621 \u0627\u0635\u0637\u0646\u0627\u0639\u064a \U0001f916",
    "Tech":     "\u062a\u0642\u0646\u064a\u0629 \U0001f4f1",
    "Arabic":   "\u0623\u062e\u0628\u0627\u0631 \u0639\u0631\u0628\u064a\u0629 \U0001f30d",
}

HASHTAGS = {
    "Finance":  "#\u0623\u0633\u0648\u0627\u0642_\u0627\u0644\u0645\u0627\u0644 #\u0627\u0642\u062a\u0635\u0627\u062f #\u0627\u0633\u062a\u062b\u0645\u0627\u0631 #\u0628\u0648\u0631\u0635\u0629",
    "Business": "#\u0623\u0639\u0645\u0627\u0644 #\u0634\u0631\u0643\u0627\u062a #\u0646\u062a\u0627\u0626\u062c_\u0645\u0627\u0644\u064a\u0629 #\u0627\u0642\u062a\u0635\u0627\u062f",
    "AI":       "#\u0630\u0643\u0627\u0621_\u0627\u0635\u0637\u0646\u0627\u0639\u064a #AI #\u062a\u0642\u0646\u064a\u0629 #\u0645\u0633\u062a\u0642\u0628\u0644",
    "Tech":     "#\u062a\u0642\u0646\u064a\u0629 #\u062a\u0643\u0646\u0648\u0644\u0648\u062c\u064a\u0627 #\u0627\u0628\u062a\u0643\u0627\u0631",
    "Arabic":   "#\u0627\u0642\u062a\u0635\u0627\u062f #\u0623\u0639\u0645\u0627\u0644 #\u0639\u0627\u0644\u0645_\u0639\u0631\u0628\u064a",
}


def fetch_news(feed_url, max_items=2):
    try:
        feed = feedparser.parse(feed_url)
        items = []
        for entry in feed.entries[:max_items]:
            title = entry.get("title", "").strip()
            summary = entry.get("summary", entry.get("description", "")).strip()
            link = entry.get("link", "").strip()
            summary = re.sub(r'<[^>]+>', '', summary)[:300].strip()
            if title and link:
                items.append({"title": title, "summary": summary, "link": link})
        return items
    except Exception as e:
        print("RSS error: " + str(e))
        return []


def rewrite_arabic(category_label, title, summary):
    try:
        prompt_title = "ترجم هذا العنوان الاخباري الى العربية الفصحى في جملة واحدة فقط بدون اي كلام اضافي: " + title
        prompt_body = "ترجم هذا النص الاخباري الى العربية الفصحى في 2-3 جمل فقط بدون اي كلام اضافي: " + (summary if summary else title)
        title_ar = model.generate_content(prompt_title).text.strip()
        body_ar = model.generate_content(prompt_body).text.strip()
        title_ar = title_ar.splitlines()[0] if title_ar else title
        return title_ar, body_ar
    except Exception as e:
        print("Gemini error: " + str(e))
        return title, summary


def format_post(category, item):
    label = CATEGORY_LABELS.get(category, category)
    title_ar, body_ar = rewrite_arabic(label, item["title"], item["summary"])
    hashtags = HASHTAGS.get(category, "")
    post = "<b>" + title_ar + "</b>\n\n" + body_ar + "\n\n" + item["link"] + "\n\n" + hashtags
    return post


def send_telegram(message):
    url = "https://api.telegram.org/bot" + BOT_TOKEN + "/sendMessage"
    payload = {
        "chat_id": CHAT_ID,
        "text": message,
        "parse_mode": "HTML",
        "disable_web_page_preview": False,
    }
    try:
        r = requests.post(url, json=payload, timeout=15)
        return r.ok
    except Exception as e:
        print("Telegram error: " + str(e))
        return False


def main():
    today = datetime.now().strftime("%Y/%m/%d")
    print("Starting bot - " + today)

    header = (
        "\U0001f4f0 <b>\u0645\u0644\u062e\u0635 \u0623\u062e\u0628\u0627\u0631 \u0627\u0644\u064a\u0648\u0645</b>\n"
        "\U0001f4c5 " + today + "\n"
        "\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\n"
        "\u0645\u0627\u0644 \u2022 \u0623\u0639\u0645\u0627\u0644 \u2022 \u0630\u0643\u0627\u0621 \u0627\u0635\u0637\u0646\u0627\u0639\u064a \u2022 \u062a\u0642\u0646\u064a\u0629"
    )
    send_telegram(header)
    time.sleep(2)

    for category, feeds in RSS_FEEDS.items():
        all_items = []
        for feed_url in feeds:
            items = fetch_news(feed_url, max_items=2)
            all_items.extend(items)
            if len(all_items) >= 2:
                break

        if not all_items:
            continue

        label = CATEGORY_LABELS.get(category, category)
        send_telegram(label + "\n\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501")
        time.sleep(1)

        for item in all_items[:2]:
            post = format_post(category, item)
            ok = send_telegram(post)
            print(("OK: " if ok else "FAIL: ") + item["title"][:60])
            time.sleep(3)

    footer = (
        "\u2705 <b>\u0627\u0646\u062a\u0647\u0649 \u0645\u0644\u062e\u0635 \u0627\u0644\u064a\u0648\u0645</b>\n"
        "\u0634\u0627\u0631\u0643 \u0645\u0627 \u064a\u0646\u0627\u0633\u0628\u0643 \u0639\u0644\u0649 X \U0001f501"
    )
    send_telegram(footer)
    print("Done")


if __name__ == "__main__":
    main()
