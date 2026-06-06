import os
import requests
from bs4 import BeautifulSoup
from google.oauth2.credentials import Credentials
from google.auth.transport.requests import Request

# =========================
# إعدادات Blogger
# =========================
BLOG_ID = os.environ.get("BLOG_ID")
CLIENT_ID = os.environ.get("CLIENT_ID")
CLIENT_SECRET = os.environ.get("CLIENT_SECRET")
REFRESH_TOKEN = os.environ.get("REFRESH_TOKEN")

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
]


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

        # محاولة عامة لاستخراج الأخبار (تعمل مع أغلب المواقع)
        for item in soup.select("a"):
            title = item.get_text(strip=True)
            link = item.get("href")

            if not title or not link:
                continue

            if len(title) < 15:
                continue

            if link.startswith("/"):
                link = url.rstrip("/") + link

            if name == "سبأ نت":
                base = "https://www.sabanew.net"
                if not link.startswith("http"):
                    link = base + link

            articles.append({
                "title": title,
                "summary": "",
                "link": link
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
def publish_to_blogger(token, title, content, link):
    url = f"https://www.googleapis.com/blogger/v3/blogs/{BLOG_ID}/posts/"

    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json"
    }

    payload = {
        "title": title,
        "content": f"{content}<br><br><a href='{link}'>المصدر</a>"
    }

    r = requests.post(url, json=payload, headers=headers)

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

    for a in articles[:10]:  # حد أقصى للنشر

        print("نشر:", a["title"])

        publish_to_blogger(
            token,
            a["title"],
            a["summary"],
            a["link"]
        )


if __name__ == "__main__":
    main()
