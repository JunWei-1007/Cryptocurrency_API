import smtplib
import time
import subprocess
import requests
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from datetime import datetime, timezone, timedelta
from dotenv import load_dotenv
import os

load_dotenv()  # 載入 .env 檔案

# ===================== Notion 設定與發送功能 =====================
def Notion(signal_name, price, quantity, rrof_s, signal_value):
    notion_token = os.getenv("NOTION_TOKEN")
    database_id = os.getenv("NOTION_DATABASE_ID")

    # ⏰ 自動取得台灣時間並轉成 ISO 格式
    taiwan_time = datetime.now(timezone(timedelta(hours=8)))
    iso_time = taiwan_time.isoformat()

    headers = {
        "Authorization": f"Bearer {notion_token}",
        "Content-Type": "application/json",
        "Notion-Version": "2022-06-28"
    }

    payload = {
        "parent": {"database_id": database_id},
        "properties": {
            "名稱": {
                "title": [{"text": {"content": "分析結果"}}]
            },
            "日期": {
                "date": {"start": iso_time}
            },
            "選取": {
                "select": {"name": signal_name}
            },
            "目前價格": {
                "number": price
            },
            "數量": {
                "number": quantity
            },
            "RROF_s": {
                "number": rrof_s
            },
            "Signal": {
                "number": signal_value
            }
        }
    }

    response = requests.post("https://api.notion.com/v1/pages", json=payload, headers=headers)

    if response.status_code in (200, 201):
        print("✅ 成功上傳到 Notion！")
    else:
        print("❌ 上傳失敗:", response.status_code, response.text)

# ===================== Gmail 設定與發送功能 =====================
gmail_user = os.getenv("GMAIL_USER")
app_password = os.getenv("GMAIL_APP_PASSWORD")
to_email = os.getenv("TO_EMAIL")

def send_email(subject, body):
    msg = MIMEMultipart()
    msg['From'] = gmail_user
    msg['To'] = to_email
    msg['Subject'] = subject
    msg.attach(MIMEText(body, 'plain'))

    try:
        server = smtplib.SMTP_SSL('smtp.gmail.com', 465)
        server.login(gmail_user, app_password)
        server.send_message(msg)
        server.quit()
        # print('📧 郵件通知已發送')
    except Exception as e:
        print(f'❌ 郵件發送失敗：{e}')

# ===================== Telegram 設定與發送功能 =====================
BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")

def send_telegram(subject, body):
    message = f'📢 <b>{subject}</b>\n\n{body}'
    url = f'https://api.telegram.org/bot{BOT_TOKEN}/sendMessage'
    payload = {
        'chat_id': CHAT_ID,
        'text': message,
        'parse_mode': 'HTML'
    }

    try:
        requests.post(url, data=payload)
    except Exception as e:
        print(f'❌ 傳送 Telegram 時發生錯誤：{e}')

# ===================== Windows 時間同步功能 =====================
def run_command(command):
    print(f"執行：{command}")
    result = subprocess.run(command, shell=True, capture_output=True, text=True)
    print(result.stdout)
    # if result.stderr:
    #     print("⚠️ 錯誤訊息：", result.stderr)

def sync_windows_time():
    Now = time.time()
    readable_time = datetime.fromtimestamp(Now)
    send_telegram("同步時間", readable_time)

    run_command("net start w32time")
    run_command("w32tm /resync")
    run_command("w32tm /query /status")

if __name__ == '__main__':
    send_telegram("test", "test")