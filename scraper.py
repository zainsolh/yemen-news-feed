import json

news = [
    {
        "title":"خبر تجريبي",
        "link":"https://example.com",
        "source":"تجربة"
    }
]

with open("news.json","w",encoding="utf-8") as f:
    json.dump(news,f,ensure_ascii=False)
