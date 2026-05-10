"""SQLite 연결 및 세션 관리."""

from sqlmodel import Session, SQLModel, create_engine

_DB_URL = "sqlite:///./sagopalgo.db"
engine = create_engine(_DB_URL, connect_args={"check_same_thread": False})


def init_db() -> None:
    SQLModel.metadata.create_all(engine)


def get_session():
    with Session(engine) as session:
        yield session
