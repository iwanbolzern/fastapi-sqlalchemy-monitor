import pytest
from common import TestAction
from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession, async_sessionmaker, create_async_engine

from fastapi_sqlalchemy_monitor.middleware import SQLAlchemyMonitor


@pytest.fixture
def session_maker() -> tuple[async_sessionmaker[AsyncSession], AsyncEngine]:
    engine = create_async_engine("sqlite+aiosqlite://", echo=False, connect_args={"check_same_thread": False})

    return async_sessionmaker(engine), engine


@pytest.fixture
def app(session_maker: tuple[async_sessionmaker[AsyncSession], AsyncEngine]) -> FastAPI:
    app = FastAPI()

    return app


def test_middleware(app: FastAPI, session_maker: tuple[async_sessionmaker[AsyncSession], AsyncEngine]):
    @app.get("/")
    async def test_method():
        session = session_maker[0]()
        await session.execute(text("SELECT 1"))
        await session.execute(text("SELECT 1"))

    test_action = TestAction()
    app.add_middleware(SQLAlchemyMonitor, engine=session_maker[1], actions=[test_action])

    test_client = TestClient(app)

    res = test_client.get("/")
    assert res.status_code == 200

    # assert stdout is Total invocations: 2
    assert test_action.statistics.total_invocations == 2


def test_middleware_with_engine_factory(
    app: FastAPI, session_maker: tuple[async_sessionmaker[AsyncSession], AsyncEngine]
):
    @app.get("/")
    async def test_method():
        session = session_maker[0]()
        await session.execute(text("SELECT 1"))
        await session.execute(text("SELECT 1"))

    test_action = TestAction()
    app.add_middleware(SQLAlchemyMonitor, engine_factory=lambda: session_maker[1], actions=[test_action])

    test_client = TestClient(app)

    res = test_client.get("/")
    assert res.status_code == 200

    # assert stdout is Total invocations: 2
    assert test_action.statistics.total_invocations == 2
