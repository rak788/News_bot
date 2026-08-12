# News_bot 🤖📰

مجموعة أدوات أتمتة مبنية بـ Python تجمع محتوى تقني من مصادر متعددة (Reddit، نشرات بريدية، مواقع تقنية)، تعالجه بالذكاء الاصطناعي، وترسل النتيجة عبر تيليجرام تلقائياً بجدولة يومية عبر GitHub Actions.

## 💡 الفكرة
مشروع طوّرته ذاتياً كخطوة عملية للتعلم في مجال الذكاء الاصطناعي والأتمتة، رغم عدم وجود خلفية تقنية مسبقة. يحتوي الريبو على أداتين مستقلتين بغرضين مختلفين:

## ⚙️ الأداة 1 — articles_bot.py (مترجم النشرات)
يتابع نشرتين بريديتين تقنيتين (The Rundown AI, AI Valley عبر kill-the-newsletter.com)، يترجم كل مقال جديد **بالكامل** إلى العربية (بدون تلخيص أو حذف)، ويرسله عبر تيليجرام. يحتفظ بسجل (articles_history.txt) لتفادي إرسال نفس المقال مرتين.

## ⚙️ الأداة 2 — news_bot.py (اداة ارسال الاخبار)
أداة أشمل تسحب مادة خام واخبار الذكاء الاصطناعي من Reddit (LocalLLaMA, MachineLearning, PromptEngineering, StableDiffusion, Midjourney) ومصادر تقنية أخرى (the-decoder.com, Product Hunt, Maginative)، وتستخدم الذكاء الاصطناعي لتوليد **8 منشورات عن اخر الاخبار والأدوات من هذه المواقع وترسلها للتليجرام مترجمه باللغة العربية  يومياً**:
- 

النتائج تُرسل منسّقة إلى قناة تيليجرام خاصة، كمسودات جاهزة.

## 🛠️ التقنيات المستخدمة
- Python (feedparser, requests)
- Telegram Bot API
- OpenRouter API (نموذج nvidia/nemotron-3-super-120b-a12b:free)
- GitHub Actions (CI/CD & Scheduling)
- Git / GitHub

## 📁 هيكل المشروع
```
news_bot.py             # بوت ارسال الاخبار (Reddit + مصادر تقنية → 8 مسودات محتوى)
articles_bot.py         # مترجم النشرات البريدية (Rundown AI, AI Valley)
requirements.txt        # المكتبات المطلوبة
.github/workflows/      # جدولة التشغيل التلقائي
README.md
```

## 🔑 المتغيرات المطلوبة (Environment Variables)
| المتغير | الاستخدام | المصدر |
|---|---|---|
| BOT_TOKEN | يستخدمه الملفان | من @BotFather على تيليجرام |
| CHAT_ID | يستخدمه الملفان | معرّف القناة/المحادثة على تيليجرام |
| OPENROUTER_KEY | يستخدمه الملفان | من openrouter.ai |

تُضاف كـ **GitHub Secrets** عبر: Settings → Secrets and variables → Actions

⚠️ **لا تكتب أي قيمة حقيقية (توكن أو Chat ID) مباشرة داخل الكود** — استخدم os.environ.get() دائماً، وإلا تصبح مكشوفة لأي زائر للريبو العام.

## 🚀 التشغيل محلياً
```bash
pip install -r requirements.txt

# PowerShell
$env:BOT_TOKEN = "your_token"
$env:CHAT_ID = "your_chat_id"
$env:OPENROUTER_KEY = "your_key"

python news_bot.py
# أو
python articles_bot.py
```

## 📌 ملاحظة
المشروع لا يزال قيد التطوير والتحسين المستمر.
