import os
import feedparser
import requests
from google.oauth2.credentials import Credentials
from google.auth.transport.requests import Request

# 1. إعدادات المفاتيح
BLOG_ID = os.environ.get("BLOG_ID")
CLIENT_ID = os.environ.get("CLIENT_ID")
CLIENT_SECRET = os.environ.get("CLIENT_SECRET")
REFRESH_TOKEN = os.environ.get("REFRESH_TOKEN")

# 2. إضافة هوية المتصفح (مهم جداً لتجاوز الحجب)
HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36"
}

# 3. مصدر تجريبي موثوق
NEWS_URL = "https://sahaafa.net/feed"

def get_google_access_token():
    creds = Credentials(token=None, refresh_token=REFRESH_TOKEN, token_uri="https://oauth2.googleapis.com/token", client_id=CLIENT_ID, client_secret=CLIENT_SECRET)
    creds.refresh(Request())
    return creds.token

def fetch_latest_news():
    print("🛰️ جاري سحب الأخبار من صحافة نت...")
    try:
        # استخدام requests لجلب البيانات مع الهوية
        response = requests.get(NEWS_URL, headers=HEADERS, timeout=15)
        feed = feedparser.parse(response.content)
        
        print(f"📊 عدد الأخبار المكتشفة: {len(feed.entries)}")
        
        if feed.entries:
            print(f"✅ تم العثور على خبر: {feed.entries[0].title}")
            return feed.entries
        else:
            print("⚠️ الخلاصة فارغة أو تم حجب البوت!")
            return []
    except Exception as e:
        print(f"❌ خطأ تقني: {e}")
        return []

def publish_to_blogger(access_token, title, content):
    url = f"https://www.googleapis.com/blogger/v3/blogs/{BLOG_ID}/posts/"
    headers = {"Authorization": f"Bearer {access_token}", "Content-Type": "application/json"}
    post_data = {"kind": "blogger#post", "title": title, "content": content}
    response = requests.post(url, json=post_data, headers=headers)
    return response.status_code == 200

def main():
    access_token = get_google_access_token()
    articles = fetch_latest_news()
    
    if articles:
        article = articles[0]
        title = article.get("title", "خبر جديد")
        description = article.get("summary", "لا يوجد وصف")
        url = article.get("link", "")
        
        content = f"<div>{description}<br><br><a href='{url}'>رابط المصدر</a></div>"
        
        if publish_to_blogger(access_token, title, content):
            print("🎉 تم النشر بنجاح!")
        else:
            print("❌ فشل النشر.")

if __name__ == "__main__":
    main()
