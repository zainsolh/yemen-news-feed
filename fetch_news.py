import feedparser
import requests
import os
import json

# 1. جلب المتغيرات السرية المربوطة بجيت هاب
BLOG_ID = os.environ.get('BLOG_ID')
CLIENT_ID = os.environ.get('CLIENT_ID')
CLIENT_SECRET = os.environ.get('CLIENT_SECRET')
REFRESH_TOKEN = os.environ.get('REFRESH_TOKEN')

# رابط خلاصة الأخبار لوكالة سبأ نت (الأخبار المحلية كمثال)
SABA_RSS_URL = 'https://www.saba.net/ar/rss/local'

# ملف نصي مصغر سنحفظ فيه روابط الأخبار المنشورة سابقاً لمنع التكرار
DB_FILE = 'published_urls.txt'

def get_access_token():
    """توليد Access Token جديد تلقائياً باستخدام الـ Refresh Token"""
    url = "https://oauth2.googleapis.com/token"
    payload = {
        'client_id': CLIENT_ID,
        'client_secret': CLIENT_SECRET,
        'refresh_token': REFRESH_TOKEN,
        'grant_type': 'refresh_token'
    }
    response = requests.post(url, data=payload)
    if response.status_code == 200:
        return response.json().get('access_token')
    else:
        print("خطأ في تجديد صلاحية الوصول (Access Token):", response.text)
        return None

def load_published_urls():
    """تحميل روابط الأخبار التي تم نشرها سابقاً لمنع التكرار"""
    if os.path.exists(DB_FILE):
        with open(DB_FILE, 'r', encoding='utf-8') as f:
            return set(line.strip() for line in f.readlines())
    return set()

def save_published_url(url):
    """حفظ رابط الخبر الجديد في الملف بعد نشره بنجاح"""
    with open(DB_FILE, 'a', encoding='utf-8') as f:
        f.write(url + '\n')

def post_to_blogger(token, title, content):
    """إرسال الخبر ونشره في مدونة بلوجر عبر الـ API"""
    url = f"https://www.googleapis.com/blogger/v3/blogs/{BLOG_ID}/posts/"
    headers = {
        'Authorization': f'Bearer {token}',
        'Content-Type': 'application/json'
    }
    payload = {
        'kind': 'blogger#post',
        'title': title,
        'content': content,
        'labels': ['أخبار محلية', 'سبأ نت']  # الأقسام (التسميات) في بلوجر
    }
    response = requests.post(url, headers=headers, json=payload)
    if response.status_code == 200:
        print(f"✅ تم نشر الخبر بنجاح: {title}")
        return True
    else:
        print(f"❌ فشل نشر الخبر: {title}. السبب: {response.text}")
        return False

def main():
    # 1. الحصول على رمز الوصول الفعال
    access_token = get_access_token()
    if not access_token:
        return

    # 2. تحميل الأخبار المنشورة مسبقاً
    published_urls = load_published_urls()

    # 3. جلب الأخبار الحالية من سبأ نت
    print("جاري فحص الأخبار من سبأ نت...")
    feed = feedparser.parse(SABA_RSS_URL)
    
    # مراجعة آخر 10 أخبار في الموقع (مرتبة من الأحدث للأقدم)
    # سنقوم بعكسها [::-1] لنشر الأقدم أولاً ثم الأحدث لترتيب المدونة
    for entry in feed.entries[:10][::-1]:
        news_link = entry.link
        
        # إذا كان الخبر قد نُشر من قبل، تخطّاه فوراً
        if news_link in published_urls:
            continue
            
        news_title = entry.title
        # جلب المقتطف أو محتوى الخبر المتوفر في الـ RSS
        news_summary = entry.summary if 'summary' in entry else ""
        
        # تنسيق مظهر التدوينة (مقتطف نظيف + زر الانتقال للمصدر الأصلي لحمايتك وسيو الموقع)
        blog_content = f"""
        <p dir="rtl" style="text-align: right; font-size: 16px; line-height: 1.6;">{news_summary}</p>
        <br>
        <div dir="rtl" style="text-align: right;">
            <a href="{news_link}" target="_blank" style="background-color: #007bff; color: white; padding: 10px 15px; text-decoration: none; border-radius: 5px; font-weight: bold;">اقرأ الخبر كاملاً من المصدر الأصلي (سبأ نت)</a>
        </div>
        """
        
        # 4. النشر في بلوجر
        success = post_to_blogger(access_token, news_title, blog_content)
        if success:
            save_published_url(news_link)

if __name__ == "__main__":
    main()
