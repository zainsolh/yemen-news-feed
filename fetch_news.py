import os
import sys
import re
import time  # تم إضافتها لعمل فاصل زمني وتفادي الحظر 429
from bs4 import BeautifulSoup
from google.oauth2.credentials import Credentials
from google.auth.transport.requests import Request
from urllib.parse import urljoin

# استيراد المكتبة الذكية لتخطي الحماية
try:
    import cloudscraper
except ImportError:
    print("⚠️ مكتبة cloudscraper غير مثبتة! يرجى تثبيتها عبر الأمر: pip install cloudscraper")
    sys.exit(1)

# =========================
# إعدادات Blogger
# =========================
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

# =========================
# قائمة المواقع
# =========================
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

# =========================
# استخراج تفاصيل الخبر
# =========================
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

# =========================
# إدارة السجل
# =========================
def load_published_items():
    if not os.path.exists(LOG_FILE):
        return set()
    with open(LOG_FILE, "r", encoding="utf-8") as f:
        return set(line.strip() for line in f if line.strip())

def save_published_item(item):
    with open(LOG_FILE, "a", encoding="utf-8") as f:
        f.write(item + "\n")

# =========================
# جلب Google Token
# =========================
def get_google_access_token():
    import requests
    creds = Credentials(
        token=None,
        refresh_token=REFRESH_TOKEN,
        token_uri="https://oauth2.googleapis.com/token",
        client_id=CLIENT_ID,
        client_secret=CLIENT_SECRET
    )
    creds.refresh(Request())
    return creds.token

# =========================
# استخراج الأخبار الذكي
# =========================
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
                if len(articles) >= 5:
                    break
        else:
            soup = BeautifulSoup(r.text, "lxml")
            for item in soup.select("a"):
                title = item.get_text(strip=True)
                link = item.get("href")

                if not title or not link or len(title) < 15:
                    continue

                title = clean_title(title)

                # تصفية الروابط الثابتة والصفحات غير الإخبارية (خصوصاً لموقع beIN)
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

                if len(articles) >= 5:
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
            print(f"✅ تم جلب {len(items)} أخبار بنجاح")
            all_articles.extend(items)
        else:
            print(f"⚠️ لم يتم العثور على أخبار أو فشل السحب")
    return all_articles

# =========================
# نشر إلى Blogger
# =========================
def publish_to_blogger(token, title, summary, image, source, link):
    import requests
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

    html = ""
    if image:
        html += f'<img src="{image}" alt="{title}" style="max-width:100%; height:auto; display:block; margin:10px auto;"><br>'

    html += ""
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

    payload = {
        "title": title,
        "content": html,
        "labels": [source, "أخبار اليمن"]
    }

    try:
        r = requests.post(url, json=payload, headers=headers)
        print(f"بيان النشر للمقالة [{title[:20]}...]: {r.status_code}")
        
        # إذا واجهنا خطأ الحظر، نخبر المستخدم في المخرجات
        if r.status_code == 429:
            print("⚠️ تنبيه: تم تجاوز الحد المسموح به من جوجل (Rate Limit).")
            
        return r.status_code == 200
    except Exception as e:
        print(f"❌ خطأ أثناء الاتصال بـ Blogger API: {e}")
        return False

# =========================
# الدالة الرئيسية
# =========================
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

    for a in articles:
        title = a["title"].strip()
        link = a["link"].strip()

        if link in published or title in published:
            print(f"⏭️ تخطي خبر مكرر: {title[:30]}...")
            continue

        print(f"📰 جاري نشر: {title}")
        success = publish_to_blogger(token, title, a["summary"], a["image"], a["source"], link)

        if success:
            save_published_item(link)
            save_published_item(title)
            published.add(link)
            published.add(title)
            published_count += 1
            
            # ⏰ إضافة فاصل زمني (10 ثوانٍ) بعد كل عملية نشر ناجحة لتجنب حظر الـ API (429)
            print("⏳ الانتظار 10 ثوانٍ قبل المقال القادم لمنع الحظر...")
            time.sleep(10)
        else:
            # إذا فشل بسبب خطأ 429، ننتظر فترة أطول (30 ثانية) كمحاولة لتخفيف الضغط عن السيرفر
            print("⏳ فشل النشر، الانتظار 30 ثانية لتخفيف الضغط...")
            time.sleep(30)

        if published_count >= 10:
            print("🚀 تم الوصول للحد الأقصى للنشر في هذه الدورة (10 أخبار).")
            break

if __name__ == "__main__":
    main()
