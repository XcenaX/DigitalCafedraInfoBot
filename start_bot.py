from Bot import Bot
import os
from dotenv import load_dotenv

BASE_DIR = os.path.dirname(os.path.realpath(__file__))
#BASE_DIR = ""
Debug = False

load_dotenv()
TOKEN = os.getenv("TOKEN")

TELEGRAM = {
    'bot_token': TOKEN,
    "BASE_DIR": BASE_DIR,
}

TELEGRAM_BOT = Bot(TELEGRAM)
if Debug:
    TELEGRAM_BOT.start_bot()
else:
    while True:
        try:
            TELEGRAM_BOT.start_bot()
        except Exception as error:
            print(error)        
            pass
