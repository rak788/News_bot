# News_bot 🤖📰

نظام أتمتة يجمع أخبار الذكاء الاصطناعي والتقنية يومياً من عدة مصادر، يلخّصها بالعربية باستخدام الذكاء الاصطناعي، ويرسلها تلقائياً عبر تيليجرام — بدون أي تدخل يدوي.

## 💡 الفكرة
مشروع طوّرته ذاتياً كخطوة عملية للتعلم في مجال الذكاء الاصطناعي والأتمتة، رغم عدم وجود خلفية تقنية مسبقة.

## ⚙️ آلية العمل
1. **الجمع**: يسحب المحتوى من GitHub Trending وReddit وغيرها 
2. **التلخيص**: يستخدم نموذج `nvidia/nemotron-3-super-120b-a12b:free` عبر منصة OpenRouter لتلخيص المحتوى بالعربية
3. **الإرسال**: يرسل الملخص عبر بوت تيليجرام
4. **الجدولة**: يعمل تلقائياً يومياً عبر GitHub Actions (بدون سيرفر)

## 🛠️ التقنيات المستخدمة
- Python
- Telegram Bot API
- OpenRouter API
- GitHub Actions (CI/CD & Scheduling)
- Git / GitHub

## 📁 هيكل المشروع
```
news_bot.py                        # السكربت الرئيسي — التنسيق والإرسال عبر تيليجرام
articles_bot.py                    # جلب المقالات/الأخبار من GitHub Trending وReddit
requirements.txt                   # المكتبات المطلوبة
.github/workflows/                 # جدولة التشغيل التلقائي اليومي
README.md
```

## 🔑 المتغيرات المطلوبة (Environment Variables)
لتشغيل المشروع تحتاج تجهّز المتغيرات التالية:

| المتغير | المصدر |
|---|---|
| `TELEGRAM_BOT_TOKEN` | من [@BotFather](https://t.me/BotFather) على تيليجرام |
| `TELEGRAM_CHAT_ID` | من رابط `getUpdates` بعد إرسال `/start` لبوتك |
| `OPENROUTER_API_KEY` | من [openrouter.ai](https://openrouter.ai) |

عند التشغيل على GitHub Actions، تُضاف كـ **Secrets** في: `Settings → Secrets and variables → Actions`

## 🚀 التشغيل محلياً
```bash
pip install -r requirements.txt

# PowerShell
$env:TELEGRAM_BOT_TOKEN = "your_token"
$env:TELEGRAM_CHAT_ID = "your_chat_id"
$env:OPENROUTER_API_KEY = "your_key"

python news_bot.py
```

## 📌 ملاحظة
المشروع لا يزال قيد التطوير والتحسين المستمر.
