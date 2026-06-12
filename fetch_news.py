import os
import sys
import re
import time
import requests
from bs4 import BeautifulSoup
from google.oauth2.credentials import Credentials
from google.auth.transport.requests import Request
from urllib.parse import urljoin

try:
    import cloudscraper
except ImportError:
    print("⚠️ مكتبة cloudscraper غير مثبتة! يرجى تثبيتها عبر الأمر: pip install cloudscraper")
    sys.exit(1)

# ==========================================
# إعدادات ومتغيرات البيئة لمنصة Blogger
# ==========================================
BLOG_ID = os.environ.get("BLOG_ID")
CLIENT_ID = os.environ.get("CLIENT_ID")
CLIENT_SECRET = os.environ.get("CLIENT_SECRET")
REFRESH_TOKEN = os.environ.get("REFRESH_TOKEN")

LOG_FILE = "published_urls.txt"

scraper = cloudscraper.create_scraper(
    browser={
        'browser': 'chrome',
        'platform': 'windows',
        'desktop': True
    }
)

# ==========================================
# قائمة المواقع المستهدفة (12 موقعاً)
# ==========================================
SOURCES = [
    {"name": "سبأ نت", "url": "https://www.sabanew.net"},
    {"name": "المشهد اليمني", "url": "https://www.almashhad.news/rss.php"}, 
    {"name": "عدن الغد", "url": "https://adngad.net/rss/"}, 
    {"name": "صحافة نت", "url": "https://sahaafa.net"},
    {"name": "الهدهد", "url": "https://al-hudhud.net"},
    {"name": "24 بوست", "url": "http://www.24-post.com/"},
    {"name": "أنباء عدن", "url": "http://www.anbaaden.net/"},
    {"name": "الأحرار نت", "url": "http://www.al-ahrar.net/"},
    {"name": "الساحل", "url": "http://www.alsahil.net/"},
    {"name": "ArabNN", "url": "http://www.arabnn.news/"},
    {"name": "Arabkoora", "url": "http://www.arabkoora.com/"},
    {"name": "bin sport", "url": "https://www.beinsports.com/ar-mena/"} 
]

def clean_title(title):
    title = title.strip()
    title = re.sub(r'(™)([\u0600-\u06FF\w])', r'\1 \2', title)
    if "كأس العالم FIFA 2026™كأس العالم FIFA 2026™" in title:
        title = title.replace("كأس العالم FIFA 2026™كأس العالم FIFA 2026™", "كأس العالم FIFA 2026™")
    title = re.sub(r'\b(\w+)\1\b', r'\1', title)
    title = " ".join(title.split())
    return title

def is_english(text):
    if not text:
        return False
    english_chars = len(re.findall(r'[a-zA-Z]', text))
    total_chars = len(re.findall(r'[\w]', text))
    if total_chars == 0:
        return False
    return (english_chars / total_chars) > 0.5

# ==========================================
# استخراج تفاصيل الخبر (الوصف والصورة)
# ==========================================
def get_article_details(url):
    try:
        r = scraper.get(url, timeout=20)
        soup = BeautifulSoup(r.text, "lxml")

        image = ""
        description = ""

        og_image = soup.find("meta", property="og:image") or soup.find("meta", attrs={"name": "twitter:image"})
        if og_image and og_image.get("content"):
            image = og_image.get("content")

        og_desc = soup.find("meta", property="og:description") or soup.find("meta", attrs={"name": "description"})
        if og_desc and og_desc.get("content"):
            description = og_desc.get("content")

        if not description:
            p = soup.find("p")
            if p:
                description = p.get_text(" ", strip=True)

        return {
            "image": image,
            "description": description[:400]
        }
    except Exception as e:
        print(f"❌ خطأ استخراج تفاصيل الخبر من {url}: {e}")
        return {"image": "", "description": ""}

# ==========================================
# إدارة السجل لمنع التكرار
# ==========================================
def load_published_items():
    if not os.path.exists(LOG_FILE):
        return set()
    with open(LOG_FILE, "r", encoding="utf-8") as f:
        return set(line.strip() for line in f if line.strip())

def save_published_item(item):
    with open(LOG_FILE, "a", encoding="utf-8") as f:
        f.write(item + "\n")

def get_google_access_token():
    creds = Credentials(
        token=None,
        refresh_token=REFRESH_TOKEN,
        token_uri="https://oauth2.googleapis.com/token",
        client_id=CLIENT_ID,
        client_secret=CLIENT_SECRET
    )
    creds.refresh(Request())
    return creds.token

# ==========================================
# جلب الأخبار (سحب 6 كخيارات احتياطية فرعية)
# ==========================================
def scrape_site(name, url):
    try:
        r = scraper.get(url, timeout=20)
        is_rss = "xml" in r.headers.get("Content-Type", "").lower() or "rss" in url or "feed" in url
        articles = []

        if is_rss:
            soup = BeautifulSoup(r.text, "xml")
            items = soup.find_all("item")
            
            for item in items:
                title_tag = item.find("title")
                link_tag = item.find("link")
                
                if not title_tag or not link_tag:
                    continue
                
                title_text = title_tag.get_text(strip=True)
                link_text = link_tag.get_text(strip=True).strip()

                title_text = clean_title(title_text)
                if len(title_text) < 15:
                    continue

                details = get_article_details(link_text)
                articles.append({
                    "title": title_text,
                    "summary": details["description"],
                    "image": details["image"],
                    "link": link_text,
                    "source": name
                })
                
                if len(articles) >= 6:
                    break
        else:
            soup = BeautifulSoup(r.text, "lxml")
            for item in soup.select("a"):
                title = item.get_text(strip=True)
                link = item.get("href")

                if not title or not link or len(title) < 15:
                    continue

                title = clean_title(title)

                if any(x in link.lower() for x in ["contact", "about", "privacy", "policy", "category", "wp-content", "faq", "ترددات", "الأسئلة"]):
                    continue
                if any(x in title for x in ["الأسئلة الأكثر شيوعاً", "ترددات beIN", "beIN MEDIA GROUP"]):
                    continue

                link = urljoin(url, link)
                details = get_article_details(link)

                articles.append({
                    "title": title,
                    "summary": details["description"],
                    "image": details["image"],
                    "link": link,
                    "source": name
                })

                if len(articles) >= 6:
                    break
        return articles
    except Exception as e:
        print(f"❌ خطأ في سحب موقع {name}: {e}")
        return []

def fetch_latest_news():
    print("🛰️ بدء جلب الأخبار من المواقع...")
    all_articles = []
    for source in SOURCES:
        print(f"\n=== جاري الفحص: {source['name']} ===")
        items = scrape_site(source["name"], source["url"])
        if items:
            print(f"✅ تم سحب {len(items)} أخبار للفحص")
            all_articles.extend(items)
        else:
            print("⚠️ لم يتم العثور على أخبار أو فشل السحب")
    return all_articles

# ====================================================
# دالة النشر المحدثة والمصححة بالكامل لضبط محاذاة الفاصل الحتمي
# ====================================================
def publish_to_blogger(token, title, summary, image, source, link):
    url = f"https://www.googleapis.com/blogger/v3/blogs/{BLOG_ID}/posts/"
    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json"
    }

    if is_english(summary):
        direction = "ltr"
        align = "left"
    else:
        direction = "rtl"
        align = "right"

    # الحماية الأمنية من حظر الـ DNS للمصادر الرياضية المحجوبة محلياً
    if source in ["bin sport"]:
        image = ""

    # 1. المكونات التي تظهر في الواجهة الرئيسية (قبل الفاصل الحتمي)
    html = ""
    if image:
        html += f'<img src="{image}" alt="{title}" style="max-width:100%; height:auto; display:block; margin:10px auto;"><br>\n'
    else:
        html += f'<div style="background:#f8f9fa; border-left:5px solid #007bff; padding:15px; margin:10px 0; font-weight:bold; font-size:18px; text-align:center;">📢 تغطية إخبارية متميزة من موقع {source}</div><br>\n'

    # 🛑 تم الإصلاح وإعادة البناء: الفاصل الحتمي يقف بدقة هنا ليقطع ما قبله عما بعده
    html += "\n<!--more-->\n"
    
    # 2. المكونات الداخلية للخبر (تظهر فقط عند الضغط على Read More)
    html += f"""
    <p dir="{direction}" style="text-align: {align}; font-size: 16px; line-height: 1.6;">{summary}</p>
    <hr>
    <p dir="rtl" style="text-align: right;"><strong>المصدر:</strong> {source}</p>
    <p dir="rtl" style="text-align: right;">
        <a href="{link}" target="_blank" rel="nofollow noopener" style="color: #007bff; text-decoration: none; font-weight: bold;">
            اقرأ الخبر كاملاً من المصدر الأصلي
        </a>
    </p>
    """

    # تهيئة التسميات والتصنيف الآلي للرياضة
    post_labels = [source, "أخبار اليمن"]
    if source in ["bin sport", "Arabkoora"]:
        post_labels.append("رياضة")

    payload = {
        "title": title,
        "content": html,
        "labels": post_labels
    }

    try:
        r = requests.post(url, json=payload, headers=headers)
        print(f"بيان النشر للمقالة [{title[:20]}...]: {r.status_code}")
        return r.status_code == 200
    except Exception as e:
        print(f"❌ خطأ أثناء الاتصال بـ Blogger API: {e}")
        return False

# ==========================================
# الدالة الرئيسية مع ميزة الذاكرة والتنوع
# ==========================================
def main():
    if not all([BLOG_ID, CLIENT_ID, CLIENT_SECRET, REFRESH_TOKEN]):
        print("❌ خطأ: بعض متغيرات البيئة (Secrets) مفقودة!")
        return

    try:
        token = get_google_access_token()
    except Exception as e:
        print(f"❌ خطأ في تجديد كود الوصول لجوجل: {e}")
        return

    articles = fetch_latest_news()
    if not articles:
        print("❌ لا توجد أخبار جديدة للتعامل معها.")
        return

    published = load_published_items()
    
    published_count = 0
    published_per_source = {} 

    for a in articles:
        source_name = a["source"]
        
        if published_per_source.get(source_name, 0) >= 1:
            continue

        title = a["title"].strip()
        link = a["link"].strip()

        if link in published or title in published:
            print(f"⏭️ تخطي خبر مكرر من {source_name}: {title[:30]}...")
            continue

        print(f"📰 جاري نشر خبر جديد من {source_name}: {title}")
        success = publish_to_blogger(token, title, a["summary"], a["image"], source_name, link)

        if success:
            save_published_item(link)
            save_published_item(title)
            published.add(link)
            published.add(title)
            
            published_per_source[source_name] = 1 
            published_count += 1
            
            print("⏳ الانتظار 10 ثوانٍ قبل المقال القادم لمنع الحظر...")
            time.sleep(10)
        else:
            print("⏳ فشل النشر، الانتظار 30 ثانية لتخفيف الضغط...")
            time.sleep(30)

        if published_count >= 12:
            print("🚀 تم الوصول للحد الأقصى المحدث لهذه الدورة (12 أخبار متفرقة).")
            break

if __name__ == "__main__":
    main()
