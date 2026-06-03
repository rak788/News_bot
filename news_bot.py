import requests
import os

key = os.environ.get("OPENROUTER_KEY", "MISSING_KEY")
print(f"🔑 المفتاح الموجود في المتغيرات: {'موجود' if key != 'MISSING_KEY' else 'مفقود'}")

payload = {
    "model": "meta-llama/llama-3-8b-instruct:free",
    "messages": [{"role": "user", "content": "hello"}]
}
headers = {"Authorization": f"Bearer {key}", "Content-Type": "application/json"}

try:
    response = requests.post("https://openrouter.ai/api/v1/chat/completions", headers=headers, json=payload, timeout=30)
    print(f"📊 كود الحالة: {response.status_code}")
    print(f"📝 الرد الكامل: {response.text}")
except Exception as e:
    print(f"❌ خطأ في الاتصال: {e}")
