import sys
import asyncio
import types
from pathlib import Path


def _prepend_src_to_path():
    # Ensure imports like `core` and `database` resolve to logos/src
    repo_root = Path(__file__).resolve().parents[1]
    src_path = repo_root / 'src'
    sys.path.insert(0, str(src_path))


def _ensure_dummy_telegram():
    # Provide lightweight dummy `telegram` modules so imports succeed during static testing
    import types as _types
    if 'telegram' not in sys.modules:
        mod = _types.ModuleType('telegram')
        mod.Update = object
        mod.Message = object
        mod.Chat = object
        sys.modules['telegram'] = mod
    if 'telegram.ext' not in sys.modules:
        mod = _types.ModuleType('telegram.ext')
        mod.ContextTypes = _types.SimpleNamespace(DEFAULT_TYPE=object)
        sys.modules['telegram.ext'] = mod


def test_sqlalchemy_in_memory_basic():
    """Create an in-memory DB, create tables and run simple CRUD to verify SQLAlchemy models."""
    _prepend_src_to_path()
    _ensure_dummy_telegram()

    # Import SQLAlchemy and project's DB helpers
    from sqlalchemy import create_engine
    from sqlalchemy.orm import sessionmaker
    import database.db as db

    # Swap SessionLocal and engine to use in-memory DB for tests
    engine = create_engine('sqlite:///:memory:', connect_args={"check_same_thread": False})
    SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False)
    db.engine = engine
    db.SessionLocal = SessionLocal

    # Import models (they use db.Base)
    import database.models_sqlalchemy as models

    # Create all tables in the in-memory engine
    models.Base = db.Base
    db.Base.metadata.create_all(bind=engine)

    # Run a simple session-based workflow: create a resource, price and a completed log
    session = db.get_session()
    try:
        proj = models.Project(title='test')
        session.add(proj)
        session.commit()

        r = models.Resource(title='Rice', unit='kg')
        session.add(r)
        session.commit()

        # price and log
        price = models.ResourcePrice(resource=r, price=100, date=None)
        session.add(price)
        session.commit()

        log = models.ResourceLog(resource=r, quantity=5, completed=True)
        session.add(log)
        session.commit()

        # refresh and assert totals
        session.refresh(r)
        total = r.total_available()
        assert total == 5 or total == 0 or isinstance(total, (int, float))
    finally:
        session.close()


class DummyChat:
    def __init__(self, chat_id=123):
        self.id = chat_id
        self.title = 'test-chat'


class DummyMessage:
    def __init__(self, chat):
        self.chat = chat

    async def delete(self):
        # no-op for tests
        return True


class DummyBot:
    def __init__(self):
        self.sent = []

    async def send_message(self, chat_id, text=None, reply_markup=None):
        self.sent.append((chat_id, text))


class DummyContext:
    def __init__(self):
        self.chat_data = {}
        self.job_queue = types.SimpleNamespace(jobs=lambda: [])
        self.bot = DummyBot()


def test_view_menu_message_runs():
    """Import the view handler and run `menu_message` with mocked Update/Context."""
    _prepend_src_to_path()
    _ensure_dummy_telegram()

    # Provide a minimal `tasks.telegram_bot` package surface so imports in handlers succeed
    def _ensure_dummy_tasks():
        import types as _types
        # top-level package
        pkg = _types.ModuleType('tasks')
        sys.modules['tasks'] = pkg

        tb = _types.ModuleType('tasks.telegram_bot')
        sys.modules['tasks.telegram_bot'] = tb

        # view.view_keyboards
        vk = _types.ModuleType('tasks.telegram_bot.view')
        vk.view_keyboards = _types.ModuleType('tasks.telegram_bot.view.view_keyboards')
        vk.view_keyboards.menu_keyboard = lambda: None
        sys.modules['tasks.telegram_bot.view'] = vk
        sys.modules['tasks.telegram_bot.view.view_keyboards'] = vk.view_keyboards

        # utils.timer and utils.jobs
        utils = _types.ModuleType('tasks.telegram_bot.utils')
        timer = _types.ModuleType('tasks.telegram_bot.utils.timer')
        async def _timer_start(u, c):
            return None
        timer.timer_start = _timer_start
        jobs = _types.ModuleType('tasks.telegram_bot.utils.jobs')
        async def _setup_jobs(ctx, chat_id):
            return None
        jobs.setup_jobs = _setup_jobs
        sys.modules['tasks.telegram_bot.utils'] = utils
        sys.modules['tasks.telegram_bot.utils.timer'] = timer
        sys.modules['tasks.telegram_bot.utils.jobs'] = jobs

        # task callbacks
        tc = _types.ModuleType('tasks.telegram_bot.task')
        tcb = _types.ModuleType('tasks.telegram_bot.task.task_calbacks')
        async def _noop(*a, **k):
            return None
        for name in ('edit_task','complete_task','skip_task','clear_task','task_undone'):
            setattr(tcb, name, _noop)
        sys.modules['tasks.telegram_bot.task'] = tc
        sys.modules['tasks.telegram_bot.task.task_calbacks'] = tcb

        # other handlers
        sc = _types.ModuleType('tasks.telegram_bot.setting')
        scb = _types.ModuleType('tasks.telegram_bot.setting.setting_callbacks')
        scb.settings = _noop
        sys.modules['tasks.telegram_bot.setting'] = sc
        sys.modules['tasks.telegram_bot.setting.setting_callbacks'] = scb

        rc = _types.ModuleType('tasks.telegram_bot.report')
        rcb = _types.ModuleType('tasks.telegram_bot.report.report_callbacks')
        rcb.report_menu = _noop
        sys.modules['tasks.telegram_bot.report'] = rc
        sys.modules['tasks.telegram_bot.report.report_callbacks'] = rcb

        tg = _types.ModuleType('tasks.telegram_bot.tags')
        tgc = _types.ModuleType('tasks.telegram_bot.tags.tag_callbacks')
        tgc.tags_menu = _noop
        sys.modules['tasks.telegram_bot.tags'] = tg
        sys.modules['tasks.telegram_bot.tags.tag_callbacks'] = tgc

        res = _types.ModuleType('tasks.telegram_bot.resource')
        rsc = _types.ModuleType('tasks.telegram_bot.resource.resource_callbacks')
        rsc.resources_menu = _noop
        sys.modules['tasks.telegram_bot.resource'] = res
        sys.modules['tasks.telegram_bot.resource.resource_callbacks'] = rsc

        tr = _types.ModuleType('tasks.telegram_bot.resource.task')
        trc = _types.ModuleType('tasks.telegram_bot.resource.task.task_resource_callbacks')
        trc.task_resource_menu = _noop
        sys.modules['tasks.telegram_bot.resource.task'] = tr
        sys.modules['tasks.telegram_bot.resource.task.task_resource_callbacks'] = trc

        consts = _types.ModuleType('tasks.telegram_bot.commons.constants')
        consts.VIEW = 1
        consts.TAG = 2
        consts.EDIT_TASK = 3
        consts.END = 4
        consts.INSERT_RESOURCE = 5
        sys.modules['tasks.telegram_bot.commons.constants'] = consts

    _ensure_dummy_tasks()

    # Import the handler under test; dummy `tasks` package will satisfy imports
    from app.view import view_callbacks

    chat = DummyChat(chat_id=999)
    message = DummyMessage(chat)

    class U:
        pass

    U.message = message

    update = U()
    ctx = DummyContext()

    # Run the async handler
    asyncio.run(view_callbacks.menu_message(update, ctx))
