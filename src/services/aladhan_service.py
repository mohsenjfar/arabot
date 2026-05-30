import requests
from datetime import datetime, timedelta

from src.persistence.models import Task, Parent
from src.persistence.db import get_session

from commons.time_utils import TimeUtils
from commons.constants import tz
timezone = TimeUtils(tz)

timings_dict = {
    "Fajr": "نماز صبح",
    "Dhuhr": "نماز ظهر",
    "Asr": "نماز عصر", 
    "Maghrib": "نماز مغرب",
    "Isha": "نماز عشاء"
}

def retrive_aladhan_by_location(longitude, latitude):
    now = datetime.now().strftime("%d-%m-%Y")
    base_url = "https://api.aladhan.com/v1/calendar/"
    adhan_url = f"{base_url}from/{now}/to/20-03-2026?latitude={latitude}&longitude={longitude}&method=7"
    return requests.get(adhan_url)

def arabic_title_to_persian(title):
    return timings_dict[title] if title in timings_dict else None

def date_to_tuple(response):
    values = []
    for data in response.json().get('data'):
        timings = data.get('timings')
        dt = data.get('date').get('gregorian').get('date')
        for timing in timings:
            title = arabic_title_to_persian(title=timing)
            if title:
                dtt = f"{dt} {timings.get(timing)[:5]}"
                dtt = datetime.strptime(dtt, "%d-%m-%Y %H:%M") - timedelta(hours=3.5)
                dtt = timezone.make_aware(dtt)
                values.append((title, dtt))
    return values

def update_aladhan(longitude, latitude):
    response = retrive_aladhan_by_location(longitude, latitude)
    timings = date_to_tuple(response)
    session = get_session()
    parent = session.query(Parent).filter_by(title='aladhan').one_or_none()
    created = False
    if parent is None:
        parent = Parent(title='aladhan')
        session.add(parent)
        session.commit()
        created = True
    if not created:
        # delete future tasks
        for t in list(parent.tasks):
            if t.start >= timezone.now():
                session.delete(t)
        session.commit()
    tasks = [
        Task(
            parent=parent,
            summary=title,
            start=timing
        ) for title, timing in timings if timing > timezone.now()
    ]
    session.add_all(tasks)
    session.commit()

