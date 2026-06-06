import os
import feedparser
import requests

# هوية متصفح لإيهام المواقع بأن البوت إنسان
HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
}

def fetch_latest_news():
    url = "https://saba.net/rss" # تأكد من استخدام رابط RSS صحيح للمصدر
    try:
        response = requests.get(url, headers=HEADERS, timeout=15)
        feed = feedparser.parse(response.content)
        
        if feed.entries:
            print(f"✅ تم العثور على {len(feed.entries)} أخبار.")
            return feed.entries
        else:
            print("⚠️ الخلاصة فارغة.")
            return []
    except Exception as e:
        print(f"❌ خطأ: {e}")
        return []

# باقي الكود الخاص بك يظل كما هو...

