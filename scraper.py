print("SCRAPER RUNNING")
import requests
from bs4 import BeautifulSoup
import json

news = []

url = "https://www.almashhad.news/"

r = requests.get(url, timeout=20)

soup = BeautifulSoup(r.text, "html.parser")

for a in soup.find_all("a"):

    title = a.get_text(strip=True)
    link = a.get("href")

    if title and link and len(title) > 20:

        news.append({
            "title": title,
            "link": link,
            "source": "المشهد اليمني"
        })

with open("news.json", "w", encoding="utf-8") as f:
    json.dump(news[:30], f, ensure_ascii=False)
