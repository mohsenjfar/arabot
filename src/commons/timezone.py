from zoneinfo import ZoneInfo
import jdatetime
import datetime
import os

TIMEZONE = os.getenv("TIMEZONE")
CALENDAR = os.getenv("CALENDAR")
DEFAULT_LOCAL_TZ = ZoneInfo(TIMEZONE)
DEFAULT_STORAGE_TZ = datetime.timezone.utc

PERSIAN_MONTH_NAMES = [
    "فروردین", "اردیبهشت", "خرداد", "تیر", "مرداد", "شهریور",
    "مهر", "آبان", "آذر", "دی", "بهمن", "اسفند"
]
PERSIAN_WEEKDAY_NAMES = ["شنبه", "یکشنبه", "دوشنبه", "سه‌شنبه", "چهارشنبه", "پنجشنبه", "جمعه"]
PERSIAN_WEEKDAY_NAMES_SHORT = ["ش", "ی", "د", "س", "چ", "پ", "ج"]

def jnow() -> jdatetime.datetime:
    return jdatetime.datetime.now().astimezone(DEFAULT_LOCAL_TZ)

def now() -> datetime.datetime:
    return datetime.datetime.now().astimezone(DEFAULT_STORAGE_TZ)

def end_of_day(delta=0):
    tommorow = datetime.date.today() + datetime.timedelta(days = delta + 1)
    return datetime.datetime.combine(tommorow, datetime.time(0,0))

def end_of_week():
    today = jdatetime.date.today()
    weekday = today.weekday()
    days_to_weekend = 6 - weekday
    return end_of_day(delta=days_to_weekend)

def to_jal(dt: datetime.datetime) -> jdatetime.datetime:
    if not isinstance(dt, datetime.datetime):
        raise TypeError("Input must be datetime.datetime")
    return jdatetime.datetime.fromgregorian(datetime=dt).astimezone(DEFAULT_LOCAL_TZ)

def to_utc(jdt: jdatetime.datetime) -> datetime.datetime:
    if not isinstance(jdt, jdatetime.datetime) or jdt.tzinfo is None:
        raise ValueError("Input must be an instanse of tz_aware jdatetime.")
    return jdt.togregorian().astimezone(DEFAULT_STORAGE_TZ).replace(tzinfo=None)

def datetime_to_utc(dt: datetime.datetime):
    return to_utc(to_jal(dt))

def combine(jdt: jdatetime.date, t: jdatetime.time) -> jdatetime.datetime:
    return jdatetime.datetime.combine(jdt,t)

def jdate_to_str(jdt: jdatetime.date) -> str:
    if not isinstance(jdt, jdatetime.date):
        raise TypeError("Input must be jdatetime.date")
    return jdt.strftime('%Y-%m-%d')

def time_to_str(jdt: jdatetime.time) -> str:
    if not isinstance(jdt, jdatetime.time):
        raise TypeError("Input must be jdatetime.time")
    return jdt.strftime('%H:%M')

def jdatetime_to_str(jdt: jdatetime.datetime) -> str:
    if not isinstance(jdt, jdatetime.datetime):
        raise TypeError("Input must be jdatetime.datetime")
    return jdt.strftime('%Y-%m-%dT%H:%M')

def datetime_to_ical(dt: datetime.datetime) -> str:
    if not isinstance(dt, datetime.datetime):
        raise TypeError("Input must be datetime.datetime")
    return dt.strftime('%Y%m%dT%H%M')

def str_to_datetime(dt_str: datetime.datetime) -> datetime:
    return datetime.datetime.fromisoformat(dt_str)

def str_to_jdate(jdate_str: str) -> jdatetime.date:
    year, month, day = map(int, jdate_str.split('-'))
    return jdatetime.datetime(year, month, day)

def str_to_jdatetime(jdatetime_str: str) -> jdatetime.datetime:
    try:
        dt = jdatetime.datetime.fromisoformat(jdatetime_str)
        return dt.replace(tzinfo=DEFAULT_LOCAL_TZ)
    except ValueError:
        raise ValueError("Valid input pattern is <YYYY-MM-DDTHH:MM> or <YYYY-MM-DD HH:MM>")
    except Exception as e:
        raise e

def str_to_utc(jdatetime_str: str) -> datetime.datetime:
    return to_utc(str_to_jdatetime(jdatetime_str))

def gstr_to_jdatetime(datetime_str: str) -> jdatetime.datetime:
    try:
        return to_jal(datetime.datetime.fromisoformat(datetime_str))
    except ValueError:
        raise ValueError("Valid input pattern is <YYYY-MM-DDTHH:MM> or <YYYY-MM-DD HH:MM>")
    except Exception as e:
        raise e
    
def jnow_to_str():
    return jdatetime_to_str(jnow())

def to_persian_digits(s: str) -> str:
    english_digits = "0123456789"
    persian_digits = "۰۱۲۳۴۵۶۷۸۹"
    translation_table = str.maketrans(english_digits, persian_digits)
    return s.translate(translation_table)

def to_english_digits(s: str) -> str:
    english_digits = "0123456789"
    persian_digits = "۰۱۲۳۴۵۶۷۸۹"
    translation_table = str.maketrans(persian_digits, english_digits)
    return s.translate(translation_table)

def jhuman_readable(jdt: jdatetime.datetime) -> str:
    if not isinstance(jdt, jdatetime.datetime):
        raise TypeError("Input must be jdatetime.datetime")
    day_name = PERSIAN_WEEKDAY_NAMES[jdt.weekday()]
    month_name = PERSIAN_MONTH_NAMES[jdt.month - 1]
    time_str = time_to_str(jdt.time())
    output = f"{day_name} {jdt.day} {month_name} سال {jdt.year} ساعت {time_str}"
    return to_persian_digits(output)

def human_readable(dt):
    return jhuman_readable(to_jal(dt))