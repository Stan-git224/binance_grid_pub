import requests
import os
from dotenv import load_dotenv
load_dotenv()
TELEGRAM_BOT_TOKEN = os.getenv('TG_TOKEN')
TG_GROUP_ID = os.getenv('TG_GROUP_ID')

def send_telegram_message(message):
    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
    payload = {
        'chat_id': TG_GROUP_ID,
        'text': message
    }
    response = requests.post(url, data=payload)
    if response.status_code == 200:
        print("Message sent successfully.")
    else:
        print(f"Failed to send message. Error: {response.status_code}")





# 範例：發送交易通知
if __name__ == "__main__":
    price = 100
    text = f"price is {price}"
    send_telegram_message(text)
