import requests
from bs4 import BeautifulSoup
import json

url = "https://www.sabanew.net/home/ar"

headers = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/137.0 Safari/537.36",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
    "Accept-Language": "ar,en-US;q=0.9,en;q=0.8",
    "Referer": "https://www.google.com/"
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
            "source": " وكالة الانباء اليمنية سبأ"
        })

print("News found:", len(news))

with open("news.json", "w", encoding="utf-8") as f:
    json.dump(news[:30], f, ensure_ascii=False, indent=2)
