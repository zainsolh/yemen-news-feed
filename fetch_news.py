import os
import feedparser
import requests
from google.oauth2.credentials import Credentials
from google.auth.transport.requests import Request

# إعدادات Blogger
BLOG_ID = os.environ.get("BLOG_ID")
CLIENT_ID = os.environ.get("CLIENT_ID")
CLIENT_SECRET = os.environ.get("CLIENT_SECRET")
REFRESH_TOKEN = os.environ.get("REFRESH_TOKEN")

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36"
}

NEWS_SOURCES = [
    {
        "name": "صحافة نت",
        "url": "https://sahaafa.net/feed"
    },
    {
        "name": "مأرب برس",
        "url": "https://marebpress.net/rss.php"
    },
    {
        "name": "وكالة سبأ",
        "url": "https://www.sabanew.net/home/viewcategory/rss.php"
    }
]


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


def fetch_latest_news():
    print("🛰️ جاري فحص المصادر...")

    articles = []

    for source in NEWS_SOURCES:
        try:
            print(f"\n{'='*50}")
            print(f"فحص المصدر: {source['name']}")
            print(f"الرابط: {source['url']}")

            response = requests.get(
                source["url"],
                headers=HEADERS,
                timeout=20,
                allow_redirects=True
            )

            print(f"Status Code: {response.status_code}")
            print(f"Final URL: {response.url}")

            preview = response.text[:500].replace("\n", " ")
            print(f"Preview: {preview}")

            feed = feedparser.parse(response.content)

            print(f"عدد العناصر المكتشفة: {len(feed.entries)}")

            if feed.entries:
                item = feed.entries[0]

                print("✅ تم العثور على خبر:")
                print(item.get("title", "بدون عنوان"))

                item["source_name"] = source["name"]
                articles.append(item)

            else:
                print("⚠️ لم يتم العثور على أي عناصر RSS")

        except Exception as e:
            print(f"❌ خطأ في {source['name']}")
            print(str(e))

    return articles


def publish_to_blogger(access_token, title, content, link):
    url = f"https://www.googleapis.com/blogger/v3/blogs/{BLOG_ID}/posts/"

    headers = {
        "Authorization": f"Bearer {access_token}",
        "Content-Type": "application/json"
    }

    payload = {
        "kind": "blogger#post",
        "title": title,
        "content": f"""
        <p>{content}</p>
        <br>
        <a href="{link}">قراءة الخبر من المصدر</a>
        """
    }

    response = requests.post(
        url,
        json=payload,
        headers=headers
    )

    print(f"نتيجة النشر: {response.status_code}")

    if response.status_code != 200:
        print(response.text)

    return response.status_code == 200


def main():

    if not all([
        BLOG_ID,
        CLIENT_ID,
        CLIENT_SECRET,
        REFRESH_TOKEN
    ]):
        print("❌ مفاتيح Blogger غير مكتملة")
        return

    access_token = get_google_access_token()

    articles = fetch_latest_news()

    if not articles:
        print("\nℹ️ لا توجد أخبار جديدة للنشر")
        return

    print(f"\nتم العثور على {len(articles)} خبر")

    for article in articles:

        title = article.get("title", "خبر جديد")
        summary = article.get("summary", "")
        link = article.get("link", "#")

        print(f"\nمحاولة نشر: {title}")

        if publish_to_blogger(
            access_token,
            title,
            summary,
            link
        ):
            print(f"✅ تم نشر: {title}")
        else:
            print(f"❌ فشل نشر: {title}")


if __name__ == "__main__":
    main()
