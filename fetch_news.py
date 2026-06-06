import os
import feedparser
import requests
from google.oauth2.credentials import Credentials
from google.auth.transport.requests import Request

# إعدادات ثابتة
BLOG_ID = os.environ.get("BLOG_ID")
CLIENT_ID = os.environ.get("CLIENT_ID")
CLIENT_SECRET = os.environ.get("CLIENT_SECRET")
REFRESH_TOKEN = os.environ.get("REFRESH_TOKEN")
LOG_FILE = "published_urls.txt"

# هوية متصفح حقيقي لتجاوز الحجب
HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36"
}

# المصادر الموثوقة
NEWS_SOURCES = [
    {"name": "صحافة نت", "url": "https://sahaafa.net/feed"},
    {"name": "مأرب برس", "url": "https://marebpress.net/rss.php"}
]

def get_google_access_token():
    creds = Credentials(token=None, refresh_token=REFRESH_TOKEN, token_uri="https://oauth2.googleapis.com/token", client_id=CLIENT_ID, client_secret=CLIENT_SECRET)
    creds.refresh(Request())
    return creds.token

def fetch_latest_news():
    print("🛰️ جاري فحص المصادر...")
    articles = []
    for source in NEWS_SOURCES:
        try:
            # جلب البيانات مع الهوية والتوقيت المحدد
            response = requests.get(source["url"], headers=HEADERS, timeout=20)
            feed = feedparser.parse(response.content)
            
            if feed.entries:
                # نأخذ أول خبر فقط كإجراء احترازي لضمان الجودة
                item = feed.entries[0]
                item['source_name'] = source["name"]
                articles.append(item)
            else:
                print(f"⚠️ {source['name']}: لم يتم العثور على محتوى (ربما حجب أو الرابط غير متاح).")
        except Exception as e:
            print(f"❌ خطأ في {source['name']}: {e}")
    return articles

def publish_to_blogger(access_token, title, content, link):
    url = f"https://www.googleapis.com/blogger/v3/blogs/{BLOG_ID}/posts/"
    headers = {"Authorization": f"Bearer {access_token}", "Content-Type": "application/json"}
    payload = {
        "kind": "blogger#post",
        "title": title,
        "content": f"{content}<br><br><a href='{link}'>قراءة الخبر من المصدر</a>"
    }
    response = requests.post(url, json=payload, headers=headers)
    return response.status_code == 200

def main():
    if not all([BLOG_ID, CLIENT_ID, CLIENT_SECRET, REFRESH_TOKEN]):
        print("❌ خطأ: مفاتيح الإعدادات (Secrets) ناقصة.")
        return

    access_token = get_google_access_token()
    articles = fetch_latest_news()
    
    if not articles:
        print("ℹ️ لا توجد أخبار جديدة للنشر في هذه الدورة.")
        return

    for article in articles:
        if publish_to_blogger(access_token, article.get("title", "خبر جديد"), article.get("summary", ""), article.get("link", "#")):
            print(f"✅ تم نشر: {article.get('title')}")
        else:
            print(f"❌ فشل نشر: {article.get('title')}")

if __name__ == "__main__":
    main()
