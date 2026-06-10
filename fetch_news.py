import os
import requests
from bs4 import BeautifulSoup
from google.oauth2.credentials import Credentials
from google.auth.transport.requests import Request
from urllib.parse import urljoin

# =========================
# إعدادات Blogger
# =========================
BLOG_ID = os.environ.get("BLOG_ID")
CLIENT_ID = os.environ.get("CLIENT_ID")
CLIENT_SECRET = os.environ.get("CLIENT_SECRET")
REFRESH_TOKEN = os.environ.get("REFRESH_TOKEN")

LOG_FILE = "published_urls.txt"

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"
}

# =========================
# المواقع
# =========================
SOURCES = [
    {"name": "سبأ نت", "url": "https://www.sabanew.net"},
    {"name": "المشهد اليمني", "url": "https://www.almashhad.news"},
    {"name": "عدن الغد", "url": "https://www.adngad.net"},
    {"name": "صحافة نت", "url": "https://sahaafa.net"},
    {"name": "الهدهد", "url": "https://al-hudhud.net"},
    
    {"name": "24 بوست", "url": "http://www.24-post.com/"},

    {"name": "أنباء عدن", "url": "http://www.anbaaden.net/"},
    {"name": "الأحرار نت", "url": "http://www.al-ahrar.net/"},
    {"name": "الساحل", "url": "http://www.alsahil.net/"},
    {"name": "ArabNN", "url": "http://www.arabnn.news/"},
    {"name": "Arabkoora", "url": "https://www.kooora.com/?n=0&rss=1"},

    { "name": "bin sport", "url":  "https://www.beinsports.com/ar-mena"},

    ]

def get_article_details(url):
    try:
        r = requests.get(url, headers=HEADERS, timeout=20)
        soup = BeautifulSoup(r.text, "lxml")

        image = ""
        description = ""

        og_image = soup.find("meta", property="og:image")
        if og_image and og_image.get("content"):
            image = og_image.get("content")

        og_desc = soup.find("meta", property="og:description")
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
        print(f"❌ خطأ استخراج تفاصيل الخبر: {e}")
        return {
            "image": "",
            "description": ""
        }

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
# استخراج الأخبار
# =========================
def scrape_site(name, url):
    try:
        r = requests.get(url, headers=HEADERS, timeout=20)


        soup = BeautifulSoup(r.text, "lxml")

        articles = []

# تخصيص روابط beIN فقط
        if "beinsports.com" in url:
            links = soup.select("a[href*='/ar-mena/']")
            print(f"عدد روابط beIN: {len(links)}")

            for x in links[:20]:
               print("LINK:", x.get("href"))
               print("TEXT:", x.get_text(strip=True))
        else:
            links = soup.select("a")

        for item in links:
            title = item.get_text(strip=True)
            link = item.get("href")

        for item in soup.select("a"):
            title = item.get_text(strip=True)
            link = item.get("href")

            if not title or not link:
                continue

            # تجاهل الروابط الفارغة
            if link == "#" or link.startswith("javascript"):
                continue

            # تحويل الروابط النسبية إلى روابط كاملة
            link = urljoin(url, link)
            
  
    # تجاهل صفحة about
               
            if len(title) < 15:
                continue

            if link.startswith("/"):
                link = url.rstrip("/") + link

            if name == "سبأ نت" and not link.startswith("http"):
                link = "https://www.sabanew.net" + link

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
        print(f"❌ خطأ في {name}: {e}")
        return []
def fetch_latest_news():
    print("🛰️ بدء جلب الأخبار من المواقع...")

    all_articles = []

    for source in SOURCES:
        print(f"\n=== {source['name']} ===")

        items = scrape_site(source["name"], source["url"])

        if items:
            print(f"✅ تم جلب {len(items)} أخبار")
            all_articles.extend(items)
        else:
            print("⚠️ لم يتم العثور على أخبار")

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
        html += f"""
        <img src="{image}"
             alt="{title}"
             style="max-width:100%;height:auto;">

        <!--more-->
        """

    html += f"""
<p>{summary}</p>

<p><strong>المصدر:</strong> {source}</p>

<p>
<a href="{link}"
   target="_blank"
   rel="nofollow noopener">
   اقرأ الخبر كاملاً من المصدر
</a>
</p>
"""

    payload = {
        "title": title,
        "content": html,
        "labels": [
            source,
            "أخبار اليمن"
        ]
    }

    r = requests.post(
        url,
        json=payload,
        headers=headers
    )

    print("نشر:", r.status_code)

    return r.status_code == 200

    


# =========================
# main
# =========================
def main():

    if not all([BLOG_ID, CLIENT_ID, CLIENT_SECRET, REFRESH_TOKEN]):
        print("❌ Secrets ناقصة")
        return

    token = get_google_access_token()

    articles = fetch_latest_news()

    if not articles:
        print("❌ لا توجد أخبار")
        return

    published = load_published_items()

    published_count = 0

    for a in articles:

        title = a["title"].strip()
        link = a["link"].strip()

        # منع التكرار بالرابط أو العنوان
        if link in published or title in published:
            print(f"⏭️ تخطي خبر مكرر: {title}")
            continue

        print(f"📰 نشر: {title}")

        success = publish_to_blogger(
    token,
    title,
    a["summary"],
    a["image"],
    a["source"],
    link
)
        

        if success:
            save_published_item(link)
            save_published_item(title)
            published.add(link)
            published.add(title)

            published_count += 1

        if published_count >= 10:
            break


if __name__ == "__main__":
    main()
