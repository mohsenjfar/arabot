import os

CHAT = chr(0)

MAX_TELEGRAM_MSG = 3500
MAX_MODEL_TOKENS = 3000

DB_USER_NAME = os.getenv("USER_NAME")
DB_PASSWORD = os.getenv("PASSWORD")
DB_NAME = os.getenv("DB_NAME")
DB_HOST = os.getenv("DB_HOST")
DB_URL = f"postgresql://{DB_USER_NAME}:{DB_PASSWORD}@{DB_HOST}:5432/{DB_NAME}"

USER_INITIAL_GREETING = "سلام"
ASSISTANT_INITIAL_GREETING = "سلام {} جان، از آشنایی باهات خیلی خوشبختم،مایلی در مورد امکانات این ربات برات توضیح بدم؟"
USER_COMEBACK_GREETING = 'سلام، من دوباره برگشتم'
ASSISTANT_COMEBACK_GREETING = "سلام {} جان خیلی خوشحالم که دوباره میبینمت، چه کمکی از دست من بر میاد؟"
RESTART_MESSAGE = "جانم {} جان، در خدمتم؟"
STOP_BOT = "بسیار خوب {} جان، هر زمان که به من نیاز داشتی من اینجام، به امید دیدار"

MAIN_MODEL_NOT_RESPOND = "عدم دریافت اطلاعات از مدل پایه، تلاش برای ارتباط با مدل جایگزین ..."
SUB_MODEL_NOT_RESPOND = "عدم دریافت پاسخ از مدل جایگزین، لطفا دقایقی دیگر مجددا تلاش نمایید"
AI_SERVER_ERROR="خطا در فراخوانی پاسخ از مدل"

PROCESSING = 'در حال پردازش ...'
