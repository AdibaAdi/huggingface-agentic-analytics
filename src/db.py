"""Database models and helpers for Postgres."""

from __future__ import annotations

from contextlib import contextmanager
from datetime import datetime

from sqlalchemy import (
    Boolean,
    DateTime,
    ForeignKey,
    Integer,
    String,
    Text,
    UniqueConstraint,
    create_engine,
)
from sqlalchemy.orm import DeclarativeBase, Mapped, Session, mapped_column, relationship, sessionmaker

from config import get_config


class Base(DeclarativeBase):
    pass


class ModelRepo(Base):
    __tablename__ = "model_repos"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    model_id: Mapped[str] = mapped_column(String(255), unique=True, index=True)
    tag: Mapped[str] = mapped_column(String(120), index=True)
    author: Mapped[str | None] = mapped_column(String(255), nullable=True)
    likes: Mapped[int] = mapped_column(Integer, default=0)
    downloads: Mapped[int] = mapped_column(Integer, default=0)
    pipeline_tag: Mapped[str | None] = mapped_column(String(120), nullable=True)
    created_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)

    discussions: Mapped[list["Discussion"]] = relationship("Discussion", back_populates="repo")


class Discussion(Base):
    __tablename__ = "discussions"
    __table_args__ = (UniqueConstraint("repo_id", "hf_discussion_num", name="uq_repo_discussion_num"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    repo_id: Mapped[int] = mapped_column(ForeignKey("model_repos.id"), index=True)
    hf_discussion_num: Mapped[int] = mapped_column(Integer)
    title: Mapped[str] = mapped_column(Text)
    author: Mapped[str | None] = mapped_column(String(255), nullable=True)
    is_pull_request: Mapped[bool] = mapped_column(Boolean, default=False)
    status: Mapped[str] = mapped_column(String(30), default="open")
    created_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    closed_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)

    repo: Mapped[ModelRepo] = relationship("ModelRepo", back_populates="discussions")


_engine = None
_SessionLocal = None


def get_engine():
    global _engine
    if _engine is None:
        cfg = get_config()
        _engine = create_engine(cfg.database_url, future=True)
    return _engine


def init_db() -> None:
    engine = get_engine()
    Base.metadata.create_all(engine)


def get_sessionmaker():
    global _SessionLocal
    if _SessionLocal is None:
        _SessionLocal = sessionmaker(bind=get_engine(), autoflush=False, autocommit=False, future=True)
    return _SessionLocal


@contextmanager
def session_scope():
    session_cls = get_sessionmaker()
    session: Session = session_cls()
    try:
        yield session
        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()
