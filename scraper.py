import requests
from bs4 import BeautifulSoup
import json

url = "https://www.sabanew.net/home/ar"

headers = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/137.0 Safari/537.36"
}

r = requests.get(url, headers=headers, timeout=20)

print("Status:", r.status_code)
print("Length:", len(r.text))

soup = BeautifulSoup(r.text, "html.parser")

news = []
seen = set()

for a in soup.find_all("a"):

    title = a.get_text(strip=True)
    link = a.get("href")

    if not title or not link:
        continue

    if len(title) < 20:
        continue

    if not link.startswith("/story/ar/"):
        continue

    full_link = "https://www.sabanew.net" + link

    if full_link in seen:
        continue

    seen.add(full_link)

    news.append({
        "title": title,
        "link": full_link,
        "source": "وكالة الأنباء اليمنية سبأ"
    })

print("News found:", len(news))

news = news[:50]

with open("news.json", "w", encoding="utf-8") as f:
    json.dump(news, f, ensure_ascii=False, indent=2)

print("news.json saved successfully")
