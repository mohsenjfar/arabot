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

USER_NOT_ALLOWED = 'Access is restricted, please contact @mohsenjfar'

AI_SERVER_ERROR = "متاسفانه در ارتباط با سرور هوش مصنوعی مشکلی پیش آمد. لطفا دوباره تلاش کنید."
MODEL_RESPONSE_FAIL = "خطا در دریافت پاسخ از مدل"

PROCESSING = 'در حال پردازش ...'
SEARCH_DATABASE = 'در حال جستجوی پایگاه داده ...'
DATABASE_RESULTS = "مقادیر دریافتی از پایگاه داده شامل:{}"

EDIT_ACTIVITY_PROMPT = "میخوام این فعالیت رو ویرایش کنم: {}"
EDIT_ACTIVITY_RESPONSE = "بسیار خوب {} جان، چی قراره تغییر کنه؟ بهم بگو تا تغییرش بدم"
