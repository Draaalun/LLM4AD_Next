"""
数据库引擎与会话管理。

提供两套独立的数据库引擎：
- FastAPI 使用 psycopg3 + 连接池（高性能同步访问）
- Celery 使用 psycopg2 + NullPool（兼容 gevent 协程）
"""

from contextlib import contextmanager

from sqlalchemy.pool import NullPool
from sqlmodel import Session, create_engine

from app.core.config import settings

# FastAPI 使用的引擎（带连接池，psycopg3）
engine = create_engine(str(settings.SQLALCHEMY_DATABASE_URI), pool_pre_ping=True)

# Celery 任务使用的引擎：psycopg2 + NullPool
# 原因：psycopg3 的 C 扩展 (psycopg_binary) I/O 在 libpq 层完成，
# gevent monkey-patch 无法拦截，多 greenlet 并发时会报
# "another command is already in progress"。
# psycopg2 使用 Python 层 socket，与 gevent 完全兼容。
_celery_db_uri = str(settings.SQLALCHEMY_DATABASE_URI).replace("postgresql+psycopg", "postgresql+psycopg2")
celery_engine = create_engine(_celery_db_uri, poolclass=NullPool)


@contextmanager
def get_db_session():
    """为 Celery 任务提供数据库会话（psycopg2 + NullPool）。

    使用上下文管理器确保会话在使用完毕后自动关闭。
    """
    with Session(celery_engine) as db:
        yield db
