"""
db.py  -  database layer. Writes to Supabase Postgres via DATABASE_URL,
falls back to a local SQLite file when DATABASE_URL is unset (for testing).

V3 models are additive: the existing Role/Run/Company tables remain intact so
worker.py and worker_v2.py can continue operating while the profile-driven V3
pipeline is tested in parallel.
"""

import os
import datetime as dt

from sqlalchemy import (create_engine, Column, Integer, String, Text, Date,
                        DateTime, JSON, Boolean, ForeignKey, UniqueConstraint)
from sqlalchemy.orm import declarative_base, sessionmaker

DATABASE_URL = os.environ.get("DATABASE_URL", "sqlite:///cache.db")
if DATABASE_URL.startswith("postgres://"):
    DATABASE_URL = DATABASE_URL.replace("postgres://", "postgresql://", 1)

_args = {"check_same_thread": False} if DATABASE_URL.startswith("sqlite") else {}
engine = create_engine(DATABASE_URL, future=True, pool_pre_ping=True, connect_args=_args)
Session = sessionmaker(bind=engine, future=True)
Base = declarative_base()


# ---------------------------------------------------------------------------
# Existing V1/V2 tables — do not remove until V3 is validated.

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


# ---------------------------------------------------------------------------
# V3 additive tables — discovery data is separated from candidate matching.

class User(Base):
    __tablename__ = "users"
    id = Column(Integer, primary_key=True)
    email = Column(String(320), unique=True, nullable=False)
    created_at = Column(DateTime, default=dt.datetime.utcnow, nullable=False)
    last_login_at = Column(DateTime)


class Profile(Base):
    __tablename__ = "profiles"
    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    name = Column(String(120), nullable=False)
    career_field = Column(String(60), nullable=False, index=True)
    target_titles = Column(JSON, default=list)
    conditional_titles = Column(JSON, default=list)
    excluded_titles = Column(JSON, default=list)
    preferred_locations = Column(JSON, default=list)
    remote_preference = Column(String(40), default="canada_remote")
    max_required_years = Column(Integer, default=4)
    salary_min = Column(Integer)
    work_authorization = Column(JSON, default=dict)
    skills = Column(JSON, default=list)
    certifications = Column(JSON, default=list)
    active = Column(Boolean, default=True, nullable=False)
    created_at = Column(DateTime, default=dt.datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=dt.datetime.utcnow,
                        onupdate=dt.datetime.utcnow, nullable=False)


class Job(Base):
    """Raw employer job record. Contains no candidate-specific score."""
    __tablename__ = "jobs"
    id = Column(Integer, primary_key=True)
    company_id = Column(Integer, ForeignKey("companies.id"), index=True)
    company_name = Column(String(200))
    source_platform = Column(String(40), index=True)
    source_external_id = Column(String(300))
    title = Column(String(400), nullable=False)
    location_raw = Column(String(300))
    workplace_type = Column(String(40))      # onsite | hybrid | remote | unknown
    url = Column(Text, nullable=False, unique=True)
    posted_at = Column(Date)
    description = Column(Text)
    captured_at = Column(DateTime, default=dt.datetime.utcnow, nullable=False)
    last_seen_at = Column(DateTime, default=dt.datetime.utcnow, nullable=False)
    active = Column(Boolean, default=True, nullable=False, index=True)


class Resume(Base):
    __tablename__ = "resumes"
    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    profile_id = Column(Integer, ForeignKey("profiles.id"), index=True)
    parent_resume_id = Column(Integer, ForeignKey("resumes.id"))
    job_id = Column(Integer, ForeignKey("jobs.id"), index=True)
    resume_type = Column(String(30), nullable=False, default="master")  # master | tailored
    filename = Column(String(300))
    storage_path = Column(Text)
    parsed_text = Column(Text)
    structured_content = Column(JSON)
    created_at = Column(DateTime, default=dt.datetime.utcnow, nullable=False)


class JobMatch(Base):
    __tablename__ = "job_matches"
    __table_args__ = (
        UniqueConstraint("profile_id", "job_id", name="uq_job_match_profile_job"),
    )

    id = Column(Integer, primary_key=True)
    profile_id = Column(Integer, ForeignKey("profiles.id"), nullable=False, index=True)
    job_id = Column(Integer, ForeignKey("jobs.id"), nullable=False, index=True)
    overall_score = Column(Integer, nullable=False)
    skills_score = Column(Integer, nullable=False)
    location_score = Column(Integer, nullable=False)
    experience_score = Column(Integer, nullable=False)
    opportunity_score = Column(Integer, nullable=False)
    eligibility_status = Column(String(20), nullable=False)  # pass | warning | fail
    recommendation = Column(String(30), nullable=False, index=True)
    matched_skills = Column(JSON, default=list)
    missing_skills = Column(JSON, default=list)
    warnings = Column(JSON, default=list)
    explanation = Column(JSON, default=dict)
    evaluated_at = Column(DateTime, default=dt.datetime.utcnow, nullable=False)


class Application(Base):
    __tablename__ = "applications"
    __table_args__ = (
        UniqueConstraint("user_id", "job_id", name="uq_application_user_job"),
    )

    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    profile_id = Column(Integer, ForeignKey("profiles.id"), nullable=False, index=True)
    job_id = Column(Integer, ForeignKey("jobs.id"), nullable=False, index=True)
    match_id = Column(Integer, ForeignKey("job_matches.id"))
    tailored_resume_id = Column(Integer, ForeignKey("resumes.id"))
    status = Column(String(30), nullable=False, default="saved", index=True)
    applied_at = Column(DateTime)
    notes = Column(Text)
    created_at = Column(DateTime, default=dt.datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=dt.datetime.utcnow,
                        onupdate=dt.datetime.utcnow, nullable=False)


def init_db():
    Base.metadata.create_all(engine)
