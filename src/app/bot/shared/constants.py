ACTIVITY = chr(0)
LLM = chr(1)
EDIT_MENU = chr(2)
EDIT_FIELD = chr(3)
RESOURCE_MENU = chr(4)
RESOURCE_QTY = chr(5)
RESOURCE_HOME = chr(6)
RESOURCE_DETAIL = chr(7)
RESOURCE_FIELD = chr(8)
RESOURCE_TAG = chr(9)
RESOURCE_PRICE = chr(10)
RESOURCE_DELETE = chr(11)
ARCHIVE_BROWSE = chr(12)
TAG_HOME = chr(13)
TAG_EDIT = chr(14)
TAG_CONFIRM = chr(15)

MAX_TELEGRAM_MSG = 3500

# Persistent reply-keyboard button labels (see commons.main_reply_keyboard) -
# a tap sends this exact text as a plain message, recognized and dispatched
# to the matching /command handler by message_handlers.command_keyboard_message_handler.
CMD_LABEL_REPORT = "/report"
CMD_LABEL_RESOURCE = "/resources"
CMD_LABEL_ARCHIVE = "/archive"
CMD_LABEL_TAGS = "/tags"
CMD_LABEL_TIMER = "/timer"
CMD_LABEL_HELP = "/help"
CMD_LABEL_STOP = "/stop"

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

# Manual (button-driven, no LLM) resource management - opened by /resource.
RESOURCE_HOME_TEXT = "برای دیدن/ویرایش منابع موجود 🔍 رو بزن، برای تعریف یه منبع جدید ➕ رو بزن"
RESOURCE_ADD_PROMPT = "عنوان منبع جدید رو بفرست"
RESOURCE_UNIT_PROMPT = "واحد جدید رو بفرست"
RESOURCE_PANTRY_PROMPT = "حداقل موجودی جدید رو بفرست"
RESOURCE_PANTRY_INVALID = "یه عدد معتبر بفرست"
RESOURCE_PRICE_PROMPT = "قیمت جدید رو بفرست"
RESOURCE_PRICE_INVALID = "یه عدد معتبر بفرست"
RESOURCE_PARITY_UNIT_PROMPT = "واحد مصرف رو بفرست (مثلا اگه این منبع به کیلوگرم انبار میشه ولی به عدد مصرف میشه)"
RESOURCE_PARITY_FACTOR_PROMPT = "ضریب تبدیل رو بفرست (هر ۱ واحد ذخیره برابر با چند واحد مصرفه)"
RESOURCE_PARITY_INVALID = "یه عدد معتبر بفرست"
RESOURCE_DELETE_CONFIRM_TEXT = "توجه! این کار منبع و کل سابقه‌ی مصرفش رو کاملا حذف می‌کنه. مطمئنی؟"
RESOURCE_DELETED = "منبع «{}» حذف شد"
RESOURCE_NOT_FOUND = "این منبع پیدا نشد"

# /archive - browsing archived activities is inline-query only (see the 🗃️
# button in the ✏️ menu for archiving one).
ARCHIVE_PROMPT_TEXT = "برای دیدن فعالیت‌های آرشیو شده 🔍 رو بزن - انتخاب هرکدوم از آرشیو خارجش می‌کنه"
ARCHIVE_DONE = "«{}» آرشیو شد"
ARCHIVE_RESTORED = "«{}» از آرشیو خارج شد"
ARCHIVE_NOT_FOUND = "این فعالیت پیدا نشد"

# /tags - manual tag management, mirrors legacy-bot-version's tag_conversation.
TAGS_HOME_TEXT = "لیست تگ‌های منابع اینجاست، برای افزودن یکی جدید ➕ رو بزن یا با 🔍 یکی رو برای ویرایش پیدا کن"
TAG_ADD_PROMPT = "عنوان تگ جدید رو بفرست"
TAG_EDIT_TEXT = "عنوان: {}\n\nبرای تغییر عنوان، عنوان جدید رو بفرست یا 🗑️ رو بزن"
TAG_RENAME_CONFIRM = "عنوان از «{}» به «{}» تغییر کنه؟"
TAG_DELETED = "تگ «{}» حذف شد"
TAG_NOT_FOUND = "این تگ پیدا نشد"

# Manual (button-driven, no LLM) edit menu - opened by the ✏️ button.
EDIT_MENU_TEXT = "چی رو می‌خوای ویرایش کنی؟"
EDIT_SUMMARY_PROMPT = "عنوان فعلی:\n<code>{}</code>\n\nعنوان جدید رو بفرست"
EDIT_DESCRIPTION_PROMPT = "توضیحات فعلی:\n<code>{}</code>\n\nتوضیحات جدید رو بفرست، یا برای مشورت با هوش مصنوعی 🤖 رو بزن"
EDIT_DATE_PROMPT_TIME = "ساعت جدید رو به فرمت HH:MM بفرست"
EDIT_DATE_INVALID_TIME = "فرمت ساعت نامعتبره، به شکل HH:MM بفرست (مثلا 14:30)"
COPY_DONE = "یه کپی از «{}» ساخته شد 🟠🔵"

# 🔄 frequency and 🤖 description-consult both hand off to the LLM (edit_activity
# tool) instead of the manual text-prompt path other fields use - recurrence
# rules and free-form description drafting are language-parsing tasks.
EDIT_FREQ_AI_PROMPT = "میخوام تکرار این فعالیت رو تغییر بدم: {}"
EDIT_FREQ_AI_RESPONSE = "بسیار خوب {} عزیز، این فعالیت قراره با چه تکراری انجام بشه؟"
EDIT_DESCRIPTION_AI_PROMPT = "میخوام در مورد توضیحات این فعالیت با هوش مصنوعی مشورت کنم: {}"
EDIT_DESCRIPTION_AI_RESPONSE = "بسیار خوب {} عزیز، در مورد توضیحات این فعالیت چی می‌خوای بپرسی یا تغییر بدی؟"

# Manual resource-link menu - opened by the 🧺 button.
RESOURCE_EMPTY = "این فعالیت فعلا به هیچ منبعی وصل نیست"
RESOURCE_LINKS_HEADER = "منابع مرتبط با این فعالیت:"
RESOURCE_QTY_PROMPT = "چقدر از «{}» با هر تایید این فعالیت اضافه یا کم بشه؟ (برای کاهش عدد منفی بگو)"
RESOURCE_QTY_INVALID = "یه عدد معتبر بفرست"
RESOURCE_REMOVED = "منبع «{}» از این فعالیت جدا شد"
