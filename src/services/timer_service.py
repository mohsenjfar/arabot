
from datetime import datetime, timedelta, date, time
from database.models_sqlalchemy import Parent, Task
from database.db import get_session
import itertools as it
from telegram import Update
from telegram.ext import ContextTypes

from core.time_utils import TimeUtils
from app.bot.shared.constants import tz
timezone = TimeUtils(tz)

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
    session = get_session()
    parent = Parent(project_id=abs(query.message.chat_id), title="timer")
    session.add(parent)
    session.commit()
    while time(18,30) > after[0].time():
        before = next(iters)
        after = next(iters_)
        if timezone.now().time() < after[0].time():
            task = Task(parent=parent, summary=before[1], start=before[0])
            session.add(task)
    session.commit()
    await query.message.delete()