"""
应用启动前置检查。

在应用启动前检测数据库连接是否可用，采用重试机制等待数据库就绪。
最多尝试 5 分钟，每秒重试一次。
"""

import logging

from sqlalchemy import Engine
from sqlmodel import Session, select
from tenacity import after_log, before_log, retry, stop_after_attempt, wait_fixed

from app.core.db import engine

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# 重试配置：最多尝试 300 次（5 分钟），每次间隔 1 秒
max_tries = 60 * 5
wait_seconds = 1


@retry(
    stop=stop_after_attempt(max_tries),
    wait=wait_fixed(wait_seconds),
    before=before_log(logger, logging.INFO),
    after=after_log(logger, logging.WARN),
)
def init(db_engine: Engine) -> None:
    """尝试连接数据库，失败时自动重试。"""
    try:
        with Session(db_engine) as session:
            session.exec(select(1))
    except Exception as e:
        logger.error(e)
        raise e


def pre_start() -> None:
    """执行启动前初始化检查。"""
    logger.info("开始初始化服务...")
    init(engine)
    logger.info("服务初始化完成")
