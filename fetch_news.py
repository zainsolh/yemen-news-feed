import os
import requests
from bs4 import BeautifulSoup
from google.oauth2.credentials import Credentials
from google.auth.transport.requests import Request
from urllib.parse import urljoin  # تم إضافتها لإصلاح الروابط الناقصة تلقائياً

# =========================
# إعدادات Blogger
# =========================
BLOG_ID = os.environ.get("BLOG_ID")
CLIENT_ID = os.environ.get("CLIENT_ID")
CLIENT_SECRET = os.environ.get("CLIENT_SECRET")
REFRESH_TOKEN = os.environ.get("REFRESH_TOKEN")

LOG_FILE = "published_urls.txt"

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
}

# =========================
# المواقع (تم تحديث بعضها لروابط RSS لاستقرار أعلى)
# =========================
SOURCES = [
    {"name": "سبأ نت", "url": "https://www.sabanew.net"},
    {"name": "المشهد اليمني", "url": "https://www.almashhad.news/rss.php"}, # يدعم RSS
    {"name": "عدن الغد", "url": "https://adngad.net/rss/"}, # يدعم RSS
    {"name": "صحافة نت", "url": "https://sahaafa.net"},
    {"name": "الهدهد", "url": "https://al-hudhud.net"},
    {"name": "24 بوست", "url": "http://www.24-post.com/"},
    {"name": "أنباء عدن", "url": "http://www.anbaaden.net/"},
    {"name": "الأحرار نت", "url": "http://www.al-ahrar.net/"},
    {"name": "الساحل", "url": "http://www.alsahil.net/"},
    {"name": "ArabNN", "url": "http://www.arabnn.news/"},
    {"name": "Arabkoora", "url": "https://www.kooora.com/?n=0&rss=1"},

    { "name": "bin sport", "url":  "https://www.beinsports.com/ar-mena"}
    
]

# =========================
# استخراج تفاصيل الخبر (الصورة والوصف)
# =========================
def get_article_details(url):
    try:
        r = requests.get(url, headers=HEADERS, timeout=20)
        soup = BeautifulSoup(r.text, "lxml")

        image = ""
        description = ""

        # محاولة جلب الصورة من وسوم الميتا (OG)
        og_image = soup.find("meta", property="og:image") or soup.find("meta", attrs={"name": "twitter:image"})
        if og_image and og_image.get("content"):
            image = og_image.get("content")

        # محاولة جلب الوصف من وسوم الميتا
        og_desc = soup.find("meta", property="og:description") or soup.find("meta", attrs={"name": "description"})
        if og_desc and og_desc.get("content"):
            description = og_desc.get("content")

        # إذا لم ينجح، يبحث في أول فقرة نصية
        if not description:
            p = soup.find("p")
            if p:
                description = p.get_text(" ", strip=True)

        return {
            "image": image,
            "description": description[:400] # اقتطاع أول 400 حرف فقط
        }

    except Exception as e:
        print(f"❌ خطأ استخراج تفاصيل الخبر من {url}: {e}")
        return {"image": "", "description": ""}

# =========================
# إدارة السجل (منع التكرار)
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
# جلب Google Token للـ Blogger
# =========================
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

# =========================
# استخراج الأخبار الذكي (يدعم RSS و HTML)
# =========================
def scrape_site(name, url):
    try:
        r = requests.get(url, headers=HEADERS, timeout=20)
        # تحديد نوع المحتوى (هل هو RSS xml أم صفحة HTML عادية)
        is_rss = "xml" in r.headers.get("Content-Type", "").lower() or "rss" in url
        
        soup = BeautifulSoup(r.text, "xml" if is_rss else "lxml")
        articles = []

        if is_rss:
            # طريقة السحب من خلاصات RSS
            items = soup.find_all("item")
            for item in items:
                title = item.find("title")
                link = item.find("link")
                
                if not title or not link:
                    continue
                
                title_text = title.get_text(strip=True)
                link_text = link.get_text(strip=True)
                
                # جلب التفاصيل والصورة من رابط المقال الأصلي
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
            # طريقة السحب العادية من الـ HTML مع تحسينات قوية
            for item in soup.select("a"):
                title = item.get_text(strip=True)
                link = item.get("href")

                if not title or not link or len(title) < 15:
                    continue

                # تخطي الروابط الداخلية غير المفيدة
                if any(x in link for x in ["contact", "about", "privacy", "policy", "category"]):
                    continue

                # دمج الرابط التلقائي (يحول الرابط من /news/1 إلى الرابط الكامل للموقع تلقائياً)
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
    url = f"https://www.googleapis.com/blogger/v3/blogs/{BLOG_ID}/posts/"
    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json"
    }

    html = ""
    if image:
        html += f'<img src="{image}" alt="{title}" style="max-width:100%; height:auto; display:block; margin:10px auto;"><br>'

    html += f"""
    <p dir="rtl" style="text-align: right; font-size: 16px;">{summary}</p>
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
        return r.status_code == 200
    except Exception as e:
        print(f"❌ خطأ أثناء الاتصال بـ Blogger API: {e}")
        return False

# =========================
# الدالة الرئيسية التشغيلية
# =========================
def main():
    if not all([BLOG_ID, CLIENT_ID, CLIENT_SECRET, REFRESH_TOKEN]):
        print("❌ خطأ: بعض متغيرات البيئة (Secrets) مفقودة!")
        return

    try:
        token = get_google_access_token()
    except Exception as e:
        print(f"❌ خطأ في تجديد كود الوصول لجوجل (Token Error): {e}")
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

        if published_count >= 10:
            print("🚀 تم الوصول للحد الأقصى للنشر في هذه الدورة (10 أخبار).")
            break

if __name__ == "__main__":
    main()
