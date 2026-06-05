import requests
import os

BLOG_ID = os.environ.get('BLOG_ID')
CLIENT_ID = os.environ.get('CLIENT_ID')
CLIENT_SECRET = os.environ.get('CLIENT_SECRET')
REFRESH_TOKEN = os.environ.get('REFRESH_TOKEN')

def get_access_token():
    url = "https://oauth2.googleapis.com/token"
    payload = {
        'client_id': CLIENT_ID,
        'client_secret': CLIENT_SECRET,
        'refresh_token': REFRESH_TOKEN,
        'grant_type': 'refresh_token'
    }
    response = requests.post(url, data=payload)
    if response.status_code == 200:
        return response.json().get('access_token')
    return None

def main():
    token = get_access_token()
    if not token:
        print("❌ فشل في جلب الـ Access Token. تحقق من الـ Secrets والـ Refresh Token!")
        return

    # إرسال منشور تجريبي لبلوجر
    url = f"https://www.googleapis.com/blogger/v3/blogs/{BLOG_ID}/posts/"
    headers = {'Authorization': f'Bearer {token}', 'Content-Type': 'application/json'}
    payload = {
        'kind': 'blogger#post',
        'title': 'منشور تجريبي من بوت جيت هاب',
        'content': 'إذا رأيت هذا المنشور، فهذا يعني أن الربط البرمجي بين GitHub ومدونتك ناجح بنسبة 100%!'
    }
    res = requests.post(url, headers=headers, json=payload)
    if res.status_code == 200:
        print("✅ تم نشر المنشور التجريبي في مدونتك بنجاح!")
    else:
        print("❌ فشل النشر. السبب الإضافي من جوجل:", res.text)

if __name__ == "__main__":
    main()
