import requests
from bs4 import BeautifulSoup
import json

url = "https://www.almashhad.news/"

headers = {
    "User-Agent": "Mozilla/5.0"
}

r = requests.get(url, headers=headers, timeout=20)

print("Status:", r.status_code)
print("Length:", len(r.text))

soup = BeautifulSoup(r.text, "html.parser")

news = []

for a in soup.find_all("a"):
    title = a.get_text(strip=True)
    link = a.get("href")

    if title and link and len(title) > 20:
        news.append({
            "title": title,
            "link": link,
            "source": "المشهد اليمني"
        })

print("News found:", len(news))

with open("news.json", "w", encoding="utf-8") as f:
    json.dump(news[:30], f, ensure_ascii=False, indent=2)
