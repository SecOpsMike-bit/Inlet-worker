"""
db.py  -  database layer. Writes to Supabase Postgres via DATABASE_URL,
falls back to a local SQLite file when DATABASE_URL is unset (for testing).
"""

import os
import datetime as dt

from sqlalchemy import (create_engine, Column, Integer, String, Text, Date,
                        DateTime, JSON, Boolean)
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
    company_id = Column(Integer)
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


class Company(Base):
    __tablename__ = "companies"
    id = Column(Integer, primary_key=True)
    name = Column(String(200))
    tier = Column(Integer, default=3)
    platform = Column(String(30))          # greenhouse | lever | ashby | workday
    slug = Column(String(200))
    wd_tenant = Column(String(120))
    wd_pod = Column(String(20))
    wd_site = Column(String(120))
    location_hint = Column(String(120))
    active = Column(Boolean, default=True)
    source = Column(String(40))
    roles_found = Column(Integer, default=0)
    last_checked = Column(DateTime)
    discovered_at = Column(DateTime, default=dt.datetime.utcnow)


def init_db():
    Base.metadata.create_all(engine)
