from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base
import os

DB_URL = os.getenv("DB_URL")

# Engine and session factory
engine = create_engine(DB_URL)
SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False)

# Declarative base for models
Base = declarative_base()

def get_session():
    return SessionLocal()
