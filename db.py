"""
db.py  -  database layer. Writes to Supabase Postgres via DATABASE_URL,
falls back to a local SQLite file when DATABASE_URL is unset (for testing).
Schema matches the Supabase `roles` table.
"""

import os
import datetime as dt

from sqlalchemy import (create_engine, Column, Integer, String, Text, Date,
                        DateTime, JSON)
from sqlalchemy.orm import declarative_base, sessionmaker

DATABASE_URL = os.environ.get("DATABASE_URL", "sqlite:///cache.db")
if DATABASE_URL.startswith("postgres://"):
    DATABASE_URL = DATABASE_URL.replace("postgres://", "postgresql://", 1)

_args = {"check_same_thread": False} if DATABASE_URL.startswith("sqlite") else {}
engine = create_engine(DATABASE_URL, future=True, pool_pre_ping=True, connect_args=_args)
Session = sessionmaker(bind=engine, future=True)
Base = declarative_base()


class Role(Base):
    __tablename__ = "roles"
    id = Column(Integer, primary_key=True)
    company = Column(String(200))
    tier = Column(Integer)
    field = Column(String(60))
    role_label = Column(String(120))
    title = Column(String(400))
    location = Column(String(300))
    url = Column(Text)
    posted = Column(Date)
    opportunity_score = Column(Integer)
    landability = Column(Integer)
    realness = Column(Integer)
    level = Column(String(20))
    flags = Column(JSON)
    description = Column(Text)
    captured_at = Column(DateTime, default=dt.datetime.utcnow)


class Run(Base):
    __tablename__ = "runs"
    id = Column(Integer, primary_key=True)
    finished_at = Column(DateTime, default=dt.datetime.utcnow)
    status = Column(String(40))
    role_count = Column(Integer)
    companies_ok = Column(JSON)
    companies_failed = Column(JSON)


def init_db():
    # Creates tables if missing. On Supabase the tables already exist from the
    # schema SQL, so this is a no-op there.
    Base.metadata.create_all(engine)
