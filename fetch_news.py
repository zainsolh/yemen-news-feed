import os
import requests
import feedparser  # مكتبة معالجة خلاصات الأخبار RSS
from google.oauth2.credentials import Credentials
from google.auth.transport.requests import Request

# إعداد برامتر المدونة وجوجل من مفاتيح جيت هاب
BLOG_ID = os.environ.get("BLOG_ID")
CLIENT_ID = os.environ.get("CLIENT_ID")
CLIENT_SECRET = os.environ.get("CLIENT_SECRET")
REFRESH_TOKEN = os.environ.get("REFRESH_TOKEN")

# 1. قائمة المصادر الإخبارية (يمكنك إضافة أي مصدر جديد هنا مستقبلاً بنفس الطريقة)
NEWS_SOURCES = [
    {"name": "صحافة نت", "url": "https://sahaafa.net/feed"},
    {"name": "وكالة سبأ", "url": "https://www.sabanew.net/rss"} # ملاحظة: تأكد أن هذا هو رابط الـ RSS الرسمي لوكالة سبأ
]

# 2. إعداد ملف الذاكرة لمنع تكرار نشر نفس الخبر
PUBLISHED_LOG_FILE = "published_urls.txt"

def load_published_urls():
    """قراءة الروابط التي تم نشرها سابقاً من الملف"""
    if os.path.exists(PUBLISHED_LOG_FILE):
        with open(PUBLISHED_LOG_FILE, "r", encoding="utf-8") as f:
            return set(f.read().splitlines())
    return set()

def save_published_url(url):
    """حفظ رابط الخبر الجديد في الملف بعد نشره"""
    with open(PUBLISHED_LOG_FILE, "a", encoding="utf-8") as f:
        f.write(url + "\n")

def get_google_access_token():
    """تجديد رمز الوصول المؤقت من جوجل"""
    print("🔄 جاري تجديد رمز الوصول المؤقت...")
    creds = Credentials(
        token=None,
        refresh_token=REFRESH_TOKEN,
        token_uri="https://oauth2.googleapis.com/token",
        client_id=CLIENT_ID,
        client_secret=CLIENT_SECRET
    )
    creds.refresh(Request())
    print("✅ تم تجديد رمز الوصول بنجاح.")
    return creds.token

def fetch_latest_news():
    """المرور على كل المصادر وجلب أحدث خبر من كل مصدر"""
    print("🛰️ جاري سحب الأخبار من المصادر المحددة...")
    new_articles = []
    
    for source in NEWS_SOURCES:
        try:
            feed = feedparser.parse(source["url"])
            if feed.entries:
                # نأخذ الخبر الأول (الأحدث) من هذا المصدر
                latest_article = feed.entries[0]
                latest_article['source_name'] = source["name"] # حفظ اسم المصدر لاستخدامه في الزر
                new_articles.append(latest_article)
                print(f"📋 تم جلب أحدث خبر من: {source['name']}")
            else:
                print(f"⚠️ لا توجد أخبار جديدة في خلاصة {source['name']}.")
        except Exception as e:
            print(f"❌ خطأ أثناء قراءة خلاصة {source['name']}: {e}")
            
    return new_articles

def publish_to_blogger(access_token, title, content):
    """نشر المقال على بلوجر"""
    url = f"https://www.googleapis.com/blogger/v3/blogs/{BLOG_ID}/posts/"
    headers = {
        "Authorization": f"Bearer {access_token}",
        "Content-Type": "application/json"
    }
    post_data = {
        "kind": "blogger#post",
        "title": title,
        "content": content
    }
    response = requests.post(url, json=post_data, headers=headers)
    return response.status_code == 200

def main():
    if not all([CLIENT_ID, CLIENT_SECRET, REFRESH_TOKEN, BLOG_ID]):
        print("❌ خطأ: بعض مفاتيح GitHub Secrets مفقودة!")
        return

    access_token = get_google_access_token()
    articles = fetch_latest_news()
    published_urls = load_published_urls()
    
    # 3. نشر الأخبار المجلوبة إذا لم يتم نشرها مسبقاً
    for article in articles:
        url = article.get("link", "")
        title = article.get("title", "خبر جديد")
        
        # فحص ما إذا كان الخبر قد نُشر من قبل
        if url in published_urls:
            print(f"⏩ تم نشر هذا الخبر مسبقاً، سيتم تخطيه: {title}")
            continue
            
        description = article.get("summary", article.get("description", "اضغط على رابط المصدر لقراءة التفاصيل."))
        source_name = article.get("source_name", "المصدر")
        
        content = f"""
        <div>
            {description}
            <br><br>
            <hr>
            <p style='text-align: center;'>
                <a href='{url}' target='_blank' style='background-color: #008cba; color: white; padding: 10px 20px; text-decoration: none; border-radius: 5px; display: inline-block;'>
                    المصدر الأصلي للخبر: {source_name}
                </a>
            </p>
        </div>
        """
        
        if publish_to_blogger(access_token, title, content):
            print(f"🎉 تم النشر بنجاح: {title}")
            save_published_url(url) # حفظ الرابط في الذاكرة لمنع تكراره
        else:
            print(f"❌ فشل نشر المقال: {title}")

if __name__ == "__main__":
    main()
