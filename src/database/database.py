import os
import sys

HERE = os.path.dirname(__file__)
SRC = os.path.join(HERE, 'src')
if SRC not in sys.path:
    sys.path.insert(0, SRC)

from database.db import engine, SessionLocal, Base, get_session

def create_all():
    Base.metadata.create_all(bind=engine)

__all__ = ['engine', 'SessionLocal', 'Base', 'get_session', 'create_all']
