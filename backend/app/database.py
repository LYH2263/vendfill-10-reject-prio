from sqlalchemy import create_engine, inspect, text
from sqlalchemy.orm import DeclarativeBase, sessionmaker

from app.config import settings

engine = create_engine(settings.database_url, pool_pre_ping=True)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


class Base(DeclarativeBase):
    pass


def ensure_columns() -> None:
    """对已存在的表做幂等补列（create_all 只建新表，不改旧表）。

    blocked 以可空布尔加入，旧数据保持 NULL——即“未配置封锁”，
    不会因此冒出封锁码。
    """
    inspector = inspect(engine)
    if "lanes" not in inspector.get_table_names():
        return
    columns = {c["name"] for c in inspector.get_columns("lanes")}
    if "blocked" not in columns:
        with engine.begin() as conn:
            conn.execute(text("ALTER TABLE lanes ADD COLUMN blocked BOOLEAN"))


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
