
from datetime import datetime, timedelta, date, time
from database.models.models_shim import Parent, Task
from django.utils import timezone
import itertools as it
from telegram import Update
from telegram.ext import ContextTypes

def next_time():
    start_time = timezone.make_aware(datetime.combine(date.today(), time(2,30)))
    pattern = [25,5]*4
    texts = ['💻 Session started', '🍹 Break time'] * 4
    values = zip(pattern, texts)
    for p, t in it.cycle(values):
        yield start_time, t
        start_time += timedelta(minutes=p)

async def timer_start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    await query.answer()
    iters, iters_ = next_time(), next_time()
    after = next(iters_)
    parent = Parent.objects.create(
        project_id=abs(query.message.chat_id),
        title="timer"
    )
    while time(18,30) > after[0].time():
        before = next(iters)
        after = next(iters_)
        if timezone.now().time() < after[0].time():
            Task.objects.create(
                parent = parent,
                summary=before[1],
                start=before[0]
            )
    await query.message.delete()