import os
import sys
import re
import time
import requests
from bs4 import BeautifulSoup
from google.oauth2.credentials import Credentials
from google.auth.transport.requests import Request
from urllib.parse import urljoin

# استيراد المكتبات المطلوبة وتخطي الحجب وأتمتة المتصفح
try:
    import cloudscraper
    from selenium import webdriver
    from selenium.webdriver.common.by import By
    from selenium.webdriver.common.keys import Keys
    from selenium.webdriver.chrome.options import Options
    from selenium.webdriver.support.ui import WebDriverWait
    from selenium.webdriver.support import expected_conditions as EC
except ImportError:
    print("⚠️ مكتبات مطلوبة غير مثبتة! يرجى التأكد من تثبيت cloudscraper و selenium")
    sys.exit(1)

# ==========================================
# إعدادات ومتغيرات البيئة (Blogger & Twitter)
# ==========================================
BLOG_ID = os.environ.get("BLOG_ID")
CLIENT_ID = os.environ.get("CLIENT_ID")
CLIENT_SECRET = os.environ.get("CLIENT_SECRET")
REFRESH_TOKEN = os.environ.get("REFRESH_TOKEN")

# بيانات حساب تويتر الحقيقي بدلاً من مفاتيح الـ API
TWITTER_USERNAME = os.environ.get("TWITTER_USERNAME")
TWITTER_EMAIL = os.environ.get("TWITTER_EMAIL")
TWITTER_PASSWORD = os.environ.get("TWITTER_PASSWORD")

LOG_FILE = "published_urls.txt"

scraper = cloudscraper.create_scraper(
    browser={
        'browser': 'chrome',
        'platform': 'windows',
        'desktop': True
    }
)

# ==========================================
# قائمة المواقع المستهدفة (12 موقعاً)
# ==========================================
SOURCES = [
    {"name": "سبأ نت", "url": "https://www.sabanew.net"},
    {"name": "المشهد اليمني", "url": "https://www.almashhad.news/rss.php"}, 
    {"name": "عدن الغد", "url": "https://adngad.net/rss/"}, 
    {"name": "صحافة نت", "url": "https://sahaafa.net"},
    {"name": "الهدهد", "url": "https://al-hudhud.net"},
    {"name": "24 بوست", "url": "http://www.24-post.com/"},
    {"name": "أنباء عدن", "url": "http://www.anbaaden.net/"},
    {"name": "الأحرار نت", "url": "http://www.al-ahrar.net/"},
    {"name": "الساحل", "url": "http://www.alsahil.net/"},
    {"name": "ArabNN", "url": "http://www.arabnn.news/"},
    {"name": "Arabkoora", "url": "http://www.arabkoora.com/"},
    {"name": "bin sport", "url": "https://www.beinsports.com/ar-mena/"} 
]

def clean_title(title):
    title = title.strip()
    title = re.sub(r'(™)([\u0600-\u06FF\w])', r'\1 \2', title)
    if "كأس العالم FIFA 2026™كأس العالم FIFA 2026™" in title:
        title = title.replace("كأس العالم FIFA 2026™كأس العالم FIFA 2026™", "كأس العالم FIFA 2026™")
    title = re.sub(r'\b(\w+)\1\b', r'\1', title)
    title = " ".join(title.split())
    return title

def is_english(text):
    if not text:
        return False
    english_chars = len(re.findall(r'[a-zA-Z]', text))
    total_chars = len(re.findall(r'[\w]', text))
    if total_chars == 0:
        return False
    return (english_chars / total_chars) > 0.5

# ==========================================
# استخراج تفاصيل الخبر
# ==========================================
def get_article_details(url):
    try:
        r = scraper.get(url, timeout=20)
        soup = BeautifulSoup(r.text, "lxml")

        image = ""
        full_content = ""

        og_image = soup.find("meta", property="og:image") or soup.find("meta", attrs={"name": "twitter:image"})
        if og_image and og_image.get("content"):
            image = og_image.get("content")

        paragraphs = soup.find_all("p")
        content_lines = []

        for p in paragraphs:
            text = p.get_text(" ", strip=True)
            if len(text) > 50 and not any(x in text for x in ["جميع الحقوق محفوظة", "اقرأ أيضاً", "تابعنا على"]):
                content_lines.append(text)

        if content_lines:
            full_content = "".join([f"<p style='margin-bottom: 15px;'>{line}</p>" for line in content_lines])
        else:
            og_desc = soup.find("meta", property="og:description") or soup.find("meta", attrs={"name": "description"})
            if og_desc and og_desc.get("content"):
                full_content = f"<p>{og_desc.get('content')}</p>"

        return {"image": image, "description": full_content}
    except Exception as e:
        print(f"❌ خطأ استخراج تفاصيل الخبر من {url}: {e}")
        return {"image": "", "description": ""}

# ==========================================
# إدارة سجل منع التكرار
# ==========================================
def load_published_items():
    if not os.path.exists(LOG_FILE):
        return set()
    with open(LOG_FILE, "r", encoding="utf-8") as f:
        return set(line.strip() for line in f if line.strip())

def save_published_item(item):
    with open(LOG_FILE, "a", encoding="utf-8") as f:
        f.write(item + "\n")

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

# ==========================================
# استخراج الأخبار من المواقع
# ==========================================
def scrape_site(name, url):
    try:
        r = scraper.get(url, timeout=20)
        is_rss = "xml" in r.headers.get("Content-Type", "").lower() or "rss" in url or "feed" in url
        articles = []

        if is_rss:
            soup = BeautifulSoup(r.text, "xml")
            items = soup.find_all("item")
            
            for item in items:
                title_tag = item.find("title")
                link_tag = item.find("link")
                
                if not title_tag or not link_tag:
                    continue
                
                title_text = title_tag.get_text(strip=True)
                link_text = link_tag.get_text(strip=True).strip()

                title_text = clean_title(title_text)
                if len(title_text) < 15:
                    continue

                details = get_article_details(link_text)
                articles.append({
                    "title": title_text,
                    "summary": details["description"],
                    "image": details["image"],
                    "link": link_text,
                    "source": name
                })
                
                if len(articles) >= 6:
                    break
        else:
            soup = BeautifulSoup(r.text, "lxml")
            for item in soup.select("a"):
                title = item.get_text(strip=True)
                link = item.get("href")

                if not title or not link or len(title) < 15:
                    continue

                title = clean_title(title)

                if any(x in link.lower() for x in ["contact", "about", "privacy", "policy", "category", "wp-content", "faq", "ترددات", "الأسئلة"]):
                    continue
                if any(x in title for x in ["الأسئلة الأكثر شيوعاً", "ترددات beIN", "beIN MEDIA GROUP"]):
                    continue

                link = urljoin(url, link)
                details = get_article_details(link)

                articles.append({
                    "title": title,
                    "summary": details["description"],
                    "image": details["image"],
                    "link": link,
                    "source": name
                })

                if len(articles) >= 6:
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
            print(f"✅ تم سحب {len(items)} أخبار للفحص")
            all_articles.extend(items)
        else:
            print("⚠️ لم يتم العثور على أخبار أو فشل السحب")
    return all_articles

# =======================================================
# دالة النشر التلقائي الجديدة كلياً عبر المتصفح (Selenium)
# =======================================================
def publish_to_twitter(title, source, blogger_url):
    if not all([TWITTER_USERNAME, TWITTER_PASSWORD, TWITTER_EMAIL]):
        print("⚠️ بيانات حساب تويتر (Username/Password/Email) مفقودة، تم تخطي النشر.")
        return False

    print("🐦 جاري بدء متصفح الأتمتة للنشر على تويتر...")
    
    # إعدادات متصفح كروم ليعمل في الخلفية بدون واجهة رسومية (Headless) يناسب السيرفرات وجهازك
    chrome_options = Options()
    chrome_options.add_argument("--headless=new") 
    chrome_options.add_argument("--no-sandbox")
    chrome_options.add_argument("--disable-dev-shm-usage")
    chrome_options.add_argument("--lang=en")
    chrome_options.add_argument("user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36")

    driver = webdriver.Chrome(options=chrome_options)
    
    try:
        # 1. فتح صفحة تسجيل دخول تويتر
        driver.get("https://x.com/i/flow/login")
        wait = WebDriverWait(driver, 20)
        
        # 2. إدخال اسم المستخدم أو الإيميل
        username_field = wait.until(EC.presence_of_element_located((By.NAME, "text")))
        username_field.send_keys(TWITTER_USERNAME)
        username_field.send_keys(Keys.ENTER)
        time.sleep(3)
        
        # 3. التعامل مع خطوة الأمان الإضافية (إذا طلب الإيميل لتأكيد الهوية)
        try:
            suspicious_field = driver.find_element(By.NAME, "text")
            if suspicious_field:
                print("🔒 تويتر يطلب البريد الإلكتروني لتأكيد الهوية...")
                suspicious_field.send_keys(TWITTER_EMAIL)
                suspicious_field.send_keys(Keys.ENTER)
                time.sleep(3)
        except:
            pass # لم يطلب إيميل وتجاوز الخطوة بنجاح
            
        # 4. إدخال كلمة المرور
        password_field = wait.until(EC.presence_of_element_located((By.NAME, "password")))
        password_field.send_keys(TWITTER_PASSWORD)
        password_field.send_keys(Keys.ENTER)
        print("🔐 تم تسجيل الدخول إلى تويتر بنجاح.")
        time.sleep(5)
        
        # 5. صياغة نص التغريدة
        hashtag = source.replace(" ", "_")
        tweet_text = f"🚨 جديدنا على المدونة #{hashtag}:\n\n{title}\n\n🔗 تفاصيل الخبر في الرابط التالي:\n{blogger_url}"
        if len(tweet_text) > 270:
            tweet_text = f"🚨 جديدنا على المدونة #{hashtag}:\n\n{title[:150]}...\n\n🔗 الرابط:\n{blogger_url}"

        # 6. فتح صندوق التغريد المباشر وكتابة النص
        driver.get("https://x.com/compose/post")
        tweet_box = wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, "div[data-testid='tweetTextarea_0']")))
        tweet_box.send_keys(tweet_text)
        time.sleep(2)
        
        # 7. الضغط على زر النشر
        publish_btn = wait.until(EC.element_to_be_clickable((By.CSS_SELECTOR, "div[data-testid='tweetButton']")))
        publish_btn.click()
        
        print("🐦 ✅ تم نشر المقال بنجاح على تويتر (X) عبر أتمتة Selenium مجاناً!")
        time.sleep(5) # الانتظار لضمان إرسال التغريدة قبل إغلاق المتصفح
        return True

    except Exception as e:
        print(f"🐦 ❌ فشل النشر التلقائي عبر Selenium: {e}")
        return False
    finally:
        driver.quit() # إغلاق المتصفح بأمان من الذاكرة

# ====================================================
# دالة النشر لبلوجر
# ====================================================
def publish_to_blogger(token, title, summary, image, source, link):
    url = f"https://www.googleapis.com/blogger/v3/blogs/{BLOG_ID}/posts/"
    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json"
    }

    if is_english(summary):
        direction = "ltr"
        align = "left"
    else:
        direction = "rtl"
        align = "right"

    if source in ["bin sport"]:
        image = ""

    html = ""
    if image:
        html += f'<img src="{image}" alt="{title}" style="max-width:100%; height:auto; display:block; margin:10px auto;"><br>\n'
    else:
        html += f'<div style="background:#f8f9fa; border-left:5px solid #007bff; padding:15px; margin:10px 0; font-weight:bold; font-size:18px; text-align:center;">📢 تغطية إخبارية متمينة من موقع {source}</div><br>\n'

    html += "\n\n"

    html += f"""
    <div dir="{direction}" style="text-align: {align}; font-size: 16px; line-height: 1.8;">
        {summary}
    </div>
    <br>
    <hr>

    <p dir="rtl" style="text-align: right;"><strong>المصدر:</strong> {source}</p>
    <p dir="rtl" style="text-align: right;">
        <a href="{link}" target="_blank" rel="nofollow noopener" style="color: #007bff; text-decoration: none; font-weight: bold;">
            اقرأ الخبر كاملاً من المصدر الأصلي
        </a>
    </p>
    """

    post_labels = [source, "أخبار اليمن"]
    if source in ["bin sport", "Arabkoora"]:
        post_labels.append("رياضة")

    payload = {
        "title": title,
        "content": html,
        "labels": post_labels
    }

    try:
        r = requests.post(url, json=payload, headers=headers)
        print(f"بيان النشر للمقالة [{title[:20]}...]: {r.status_code}")
        if r.status_code == 200:
            return r.json().get("url")
        return None
    except Exception as e:
        print(f"❌ خطأ أثناء الاتصال بـ Blogger API: {e}")
        return None

# ==========================================
# الدالة الرئيسية مع ميزة النشر المزدوج
# ==========================================
def main():
    if not all([BLOG_ID, CLIENT_ID, CLIENT_SECRET, REFRESH_TOKEN]):
        print("❌ خطأ: بعض متغيرات البيئة (Secrets) لبلوجر مفقودة!")
        return

    try:
        token = get_google_access_token()
    except Exception as e:
        print(f"❌ خطأ في تجديد كود الوصول لجوجل: {e}")
        return

    articles = fetch_latest_news()
    if not articles:
        print("❌ لا توجد أخبار جديدة للتعامل معها.")
        return

    published = load_published_items()
    
    published_count = 0
    published_per_source = {} 

    for a in articles:
        source_name = a["source"]
        
        if published_per_source.get(source_name, 0) >= 1:
            continue

        title = a["title"].strip()
        link = a["link"].strip()

        if link in published or title in published:
            print(f"⏭️ تخطي خبر مكرر من {source_name}: {title[:30]}...")
            continue

        print(f"📰 جاري نشر خبر جديد من {source_name}: {title}")
        
        blogger_url = publish_to_blogger(token, title, a["summary"], a["image"], source_name, link)

        if blogger_url:
            save_published_item(link)
            save_published_item(title)
            published.add(link)
            published.add(title)
            
            published_per_source[source_name] = 1 
            published_count += 1
            
            # 🔥 النشر الفوري في تويتر عبر المتصفح التلقائي برابط بلوجر
            publish_to_twitter(title, source_name, blogger_url)
            
            print("⏳ الانتظار 15 ثانية لمنع الحظر...")
            time.sleep(15)
        else:
            print("⏳ فشل النشر في بلوجر، الانتظار 30 ثانية لتخفيف الضغط...")
            time.sleep(30)

        if published_count >= 12:
            print("🚀 تم الوصول للحد الأقصى لهذه الدورة (12 أخبار متفرقة).")
            break

if __name__ == "__main__":
    main()
