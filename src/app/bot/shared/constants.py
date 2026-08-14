ACTIVITY = chr(0)
LLM = chr(1)
EDIT_MENU = chr(2)
EDIT_FIELD = chr(3)
RESOURCE_MENU = chr(4)
RESOURCE_QTY = chr(5)

MAX_TELEGRAM_MSG = 3500

USER_INITIAL_GREETING = "سلام {} عزیز به بازوی آرا خوش جهت مشاهده راهنمای استفاده از بازو /help رو لمس کن"
USER_COMEBACK_GREETING = 'سلام {} عزیز خوشحالم که دوباره می بینمت'
RESTART_MESSAGE = "در خدمتم {} عزیز"
STOP_BOT = "بسیار خوب {} عزیز، هر زمان که به من نیاز داشتی من اینجام، به امید دیدار"

USER_NOT_ALLOWED = 'Access is restricted, please contact @mohsenjfar'

AI_SERVER_ERROR = "متاسفانه در ارتباط با سرور هوش مصنوعی مشکلی پیش آمد. لطفا دوباره تلاش کنید."

PROCESSING = 'در حال پردازش ...'
SEARCH_DATABASE = 'در حال جستجوی پایگاه داده ...'
DATABASE_RESULTS = "مقادیر دریافتی از پایگاه داده شامل:{}"

REPORT_PROMPT = "چه گزارشی می‌خوای ببینی {} عزیز؟ مثلا بگو «کارهای امروز» یا «فعالیت‌های این هفته» 📊"

RESOURCE_PROMPT = "چه منبعی می‌خوای تعریف کنی {} عزیز؟ عنوان، واحد و هر جزئیات دیگه‌ای که داره رو بهم بگو 🧺"

# Manual (button-driven, no LLM) edit menu - opened by the ✏️ button.
EDIT_MENU_TEXT = "چی رو می‌خوای ویرایش کنی؟"
EDIT_SUMMARY_PROMPT = "عنوان فعلی:\n<code>{}</code>\n\nعنوان جدید رو بفرست"
EDIT_DESCRIPTION_PROMPT = "توضیحات فعلی:\n<code>{}</code>\n\nتوضیحات جدید رو بفرست"
EDIT_FREQ_PROMPT = (
    "قانون تکرار فعلی: <code>{}</code>\n\n"
    "قانون تکرار جدید رو به فرمت RRULE بفرست (مثلا FREQ=DAILY;INTERVAL=1)\n"
    "یا برای غیرفعال کردن تکرار بنویس «بدون تکرار»"
)
EDIT_FREQ_INVALID = "قانون تکرار نامعتبره، دوباره امتحان کن"
EDIT_DATE_PROMPT_TIME = "ساعت جدید رو به فرمت HH:MM بفرست"
EDIT_DATE_INVALID_TIME = "فرمت ساعت نامعتبره، به شکل HH:MM بفرست (مثلا 14:30)"
COPY_DONE = "یه کپی از «{}» ساخته شد 🟠🔵"

# Manual resource-link menu - opened by the 🧺 button.
RESOURCE_EMPTY = "این فعالیت فعلا به هیچ منبعی وصل نیست"
RESOURCE_LINKS_HEADER = "منابع مرتبط با این فعالیت:"
RESOURCE_QTY_PROMPT = "چقدر از «{}» با هر تایید این فعالیت اضافه یا کم بشه؟ (برای کاهش عدد منفی بگو)"
RESOURCE_QTY_INVALID = "یه عدد معتبر بفرست"
RESOURCE_REMOVED = "منبع «{}» از این فعالیت جدا شد"