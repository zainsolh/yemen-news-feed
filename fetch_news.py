import os
import requests
import feedparser  # مكتبة معالجة خلاصات الأخبار RSS
from google.oauth2.credentials import Credentials
from google.auth.transport.requests import Request

# 1. إعداد برامتر المدونة وجوجل من مفاتيح جيت هاب السحرية
BLOG_ID = os.environ.get("BLOG_ID")  # معرف مدونتك على بلوجر
CLIENT_ID = os.environ.get("CLIENT_ID")
CLIENT_SECRET = os.environ.get("CLIENT_SECRET")
REFRESH_TOKEN = os.environ.get("REFRESH_TOKEN")

# رابط خلاصة الأخبار (RSS Feed) لموقع صحافة نت لجلب الأخبار الحية فور صدورها
NEWS_RSS_URL = "https://www.sabanew.net/"

def get_google_access_token():
    """
    تجديد رمز الوصول المؤقت تلقائياً باستخدام الـ Refresh Token الدائم
    """
    print("🔄 جاري تجديد رمز الوصول المؤقت من خوادم جوجل...")
    creds = Credentials(
        token=None,
        refresh_token=REFRESH_TOKEN,
        token_uri="https://oauth2.googleapis.com/token",
        client_id=CLIENT_ID,
        client_secret=CLIENT_SECRET
    )
    
    # إجبار المكتبة على طلب توكن جديد
    creds.refresh(Request())
    print("✅ تم تجديد رمز الوصول بنجاح.")
    return creds.token

def fetch_latest_news():
    """
    جلب الأخبار الجديدة وتفكيكها من خلاصة موقع صحافة نت
    """
    print("🛰️ جاري سحب آخر الأخبار من موقع صحافة نت...")
    try:
        # قراءة وتفكيك الـ RSS Feed للموقع
        feed = feedparser.parse(NEWS_RSS_URL)
        
        # التأكد من نجاح جلب البيانات ووجود أخبار
        if feed.entries:
            print(f"📋 تم العثور على {len(feed.entries)} خبر جديد في الخلاصة.")
            return feed.entries
        else:
            print("⚠️ لم يتم العثور على أخبار جديدة في خلاصة الموقع حالياً.")
            return []
    except Exception as e:
        print(f"❌ خطأ أثناء قراءة خلاصة أخبار صحافة نت: {e}")
        return []

def publish_to_blogger(access_token, title, content):
    """
    نشر المقال الجديد على مدونة بلوجر عبر Blogger API v3
    """
    url = f"https://www.googleapis.com/blogger/v3/blogs/{BLOG_ID}/posts/"
    
    headers = {
        "Authorization": f"Bearer {access_token}",
        "Content-Type": "application/json"
    }
    
    # هيكل المقال البرمجي في بلوجر
    post_data = {
        "kind": "blogger#post",
        "title": title,
        "content": content
    }
    
    response = requests.post(url, json=post_data, headers=headers)
    
    if response.status_code == 200:
        print(f"🎉 تم نشر المقال بنجاح: {title}")
    else:
        print(f"❌ فشل نشر المقال. الخطأ: {response.text}")

def main():
    # التأكد من وجود كافة المفاتيح الأساسية
    if not all([CLIENT_ID, CLIENT_SECRET, REFRESH_TOKEN, BLOG_ID]):
        print("❌ خطأ: بعض مفاتيح GitHub Secrets مفقودة! تحقق من إعداداتك.")
        return

    # 1. تجديد الـ Access Token من جوجل
    access_token = get_google_access_token()
    
    # 2. جلب الأخبار الجديدة من صحافة نت
    articles = fetch_latest_news()
    
    # 3. نشر أحدث خبر متوفر من القائمة المجلوبة
    if articles:
        # أخذ الخبر الأول الأحدث في القائمة
        latest_article = articles[0]
        
        title = latest_article.get("title", "خبر جديد")
        # جلب خلاصة النص أو الوصف المتاح للخبر
        description = latest_article.get("summary", latest_article.get("description", "اضغط على رابط المصدر لقراءة تفاصيل الخبر كاملاً."))
        url = latest_article.get("link", "")
        
        # تنسيق محتوى المقال بشكل أنيق لمدونة بلوجر مع إضافة رابط المصدر الأصلي
        content = f"""
        <div>
            {description}
            <br><br>
            <hr>
            <p style='text-align: center;'>
                <a href='{url}' target='_blank' style='background-color: #008cba; color: white; padding: 10px 20px; text-decoration: none; border-radius: 5px; display: inline-block;'>
                    المصدر الأصلي للخبر: صحافة نت
                </a>
            </p>
        </div>
        """
        
        # النشر الفعلي في مدونتك
        publish_to_blogger(access_token, title, content)
    else:
        print("ℹ️ لا توجد مقالات جديدة لنشرها في هذا التوقيت.")

if __name__ == "__main__":
    main()
