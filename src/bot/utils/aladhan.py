import requests
from datetime import datetime, timedelta
from database.models.models_shim import Task, Parent
from django.utils import timezone
commons.constants import timings_dict

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
    parent, created = Parent.objects.get_or_create(title='aladhan')
    if not created:
        parent.tasks.filter(start__gte=timezone.now()).delete()
    tasks = [
        Task(
            parent=parent,
            summary=title,
            start=timing
        ) for title, timing in timings if timing > timezone.now()
    ]
    Task.objects.bulk_create(tasks)

