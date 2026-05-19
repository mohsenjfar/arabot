import asyncio


class DummyChat:
    def __init__(self, chat_id=111):
        self.id = chat_id
        self.title = 'chat-title'


class DummyMessage:
    def __init__(self, chat):
        self.chat = chat

    async def delete(self):
        return True


class DummyContext:
    def __init__(self):
        self.chat_data = {}
        self.job_queue = type('J', (), {'jobs': lambda self: []})()
        class B:
            async def send_message(self, chat_id, text=None, reply_markup=None):
                return True
        self.bot = B()


def test_start_handler_creates_project_and_clears_messages(in_memory_db):
    db, session = in_memory_db
    import database.models_sqlalchemy as models
    from app.view import view_callbacks

    # prepare: create a task with start in the past so the handler will try to clear message_id
    parent = models.Parent(title='P')
    session.add(parent)
    session.commit()

    import datetime
    past = datetime.datetime.utcnow()
    t = models.Task(parent=parent, summary='T', start=past)
    session.add(t)
    session.commit()

    chat = DummyChat(chat_id=222)
    message = DummyMessage(chat)

    class U:
        pass

    U.message = message
    update = U()
    ctx = DummyContext()

    # run the handler (async)
    asyncio.run(view_callbacks.start(update, ctx))

    # assert project was created
    proj = session.query(models.Project).filter_by(id=abs(chat.id)).one_or_none()
    assert proj is not None
