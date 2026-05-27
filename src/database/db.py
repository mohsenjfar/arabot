from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base
import os

# Engine and session factory
engine = create_engine(os.getenv("DATABASE_URL"))
SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False)

# Declarative base for models
Base = declarative_base()

def get_session():
    return SessionLocal()
