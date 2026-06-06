import os
import requests
from google.oauth2.credentials import Credentials
from google.auth.transport.requests import Request

# إعدادات Blogger
BLOG_ID = os.environ.get("BLOG_ID")
CLIENT_ID = os.environ.get("CLIENT_ID")
CLIENT_SECRET = os.environ.get("CLIENT_SECRET")
REFRESH_TOKEN = os.environ.get("REFRESH_TOKEN")


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


LOG_FILE = "published_urls.txt"

def load_published_urls():
    if not os.path.exists(LOG_FILE):
        return set()

    with open(LOG_FILE, "r", encoding="utf-8") as f:
        return set(line.strip() for line in f if line.strip())


def save_published_url(url):
    with open(LOG_FILE, "a", encoding="utf-8") as f:
        f.write(url + "\n")


def fetch_latest_news():
    print("🧪 اختبار منع التكرار")

    return [
        {
            "title": "خبر تجريبي",
            "summary": "هذا الخبر يجب أن ينشر مرة واحدة فقط.",
            "link": "https://example.com/news1"
        }
    ]
    


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

    for article in articles:

        title = article["title"]
        summary = article["summary"]
        link = article["link"]

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
    main(published_urls = load_published_urls()

for article in articles:

    link = article["link"]

    if link in published_urls:
        print(f"⏭️ تم تخطي الخبر المنشور مسبقاً: {link}")
        continue

    title = article["title"]
    summary = article["summary"]

    print(f"\nمحاولة نشر: {title}")

    if publish_to_blogger(
        access_token,
        title,
        summary,
        link
    ):
        save_published_url(link)
        print(f"✅ تم نشر: {title}")
    else:
        print(f"❌ فشل نشر: {title}"))
