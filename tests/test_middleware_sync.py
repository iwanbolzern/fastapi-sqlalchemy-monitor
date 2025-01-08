import pytest
from common import TestAction
from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy import Engine, StaticPool, create_engine, select, text
from sqlalchemy.orm import DeclarativeBase, Mapped, Session, mapped_column, sessionmaker

from fastapi_sqlalchemy_monitor.middleware import SQLAlchemyMonitor


@pytest.fixture
def session_maker() -> tuple[sessionmaker[Session], Engine]:
    engine = create_engine("sqlite://", echo=True, connect_args={"check_same_thread": False}, poolclass=StaticPool)

    return sessionmaker(engine), engine


@pytest.fixture
def app(session_maker: tuple[sessionmaker[Session], Engine]) -> FastAPI:
    app = FastAPI()

    return app


def test_middleware(capsys, app: FastAPI, session_maker: tuple[sessionmaker[Session], Engine]):
    @app.get("/")
    def test_method():
        session = session_maker[0]()
        session.execute(text("SELECT 1"))
        session.execute(text("SELECT 1"))

    test_action = TestAction()
    app.add_middleware(SQLAlchemyMonitor, engine=session_maker[1], actions=[test_action])

    test_client = TestClient(app)

    res = test_client.get("/")
    assert res.status_code == 200

    # assert stdout is Total invocations: 2
    assert test_action.statistics.total_invocations == 2


def test_middleware_with_engine_factory(capsys, app: FastAPI, session_maker: tuple[sessionmaker[Session], Engine]):
    @app.get("/")
    def test_method():
        session = session_maker[0]()
        session.execute(text("SELECT 1"))
        session.execute(text("SELECT 1"))

    test_action = TestAction()
    app.add_middleware(SQLAlchemyMonitor, engine_factory=lambda: session_maker[1], actions=[test_action])

    test_client = TestClient(app)

    res = test_client.get("/")
    assert res.status_code == 200

    # assert stdout is Total invocations: 2
    assert test_action.statistics.total_invocations == 2


def test_middleware_orm(app: FastAPI, session_maker: tuple[sessionmaker[Session], Engine]):
    # create an ORM class
    class Base(DeclarativeBase):
        pass

    class Test(Base):
        __tablename__ = "test"
        id: Mapped[int] = mapped_column(primary_key=True)
        test_2: Mapped[str]

    # create the table
    Base.metadata.create_all(session_maker[1])

    @app.get("/")
    def test_method():
        session = session_maker[0]()
        session.bulk_save_objects([Test(test_2="test") for _ in range(10000)])
        session.execute(select(Test).where(Test.test_2 == "test"))

    test_action = TestAction()
    app.add_middleware(SQLAlchemyMonitor, engine=session_maker[1], actions=[test_action])

    test_client = TestClient(app)

    res = test_client.get("/")
    assert res.status_code == 200

    # assert stdout is Total invocations: 2
    assert test_action.statistics.total_invocations == 2
    assert test_action.statistics.total_invocation_time_ms > 0
