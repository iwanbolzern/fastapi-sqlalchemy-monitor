import logging
import time
from contextvars import ContextVar
from typing import Callable

from sqlalchemy import Engine, event
from sqlalchemy.ext.asyncio import AsyncEngine
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.types import ASGIApp

from fastapi_sqlalchemy_monitor.action import Action
from fastapi_sqlalchemy_monitor.statistics import AlchemyStatistics


class SQLAlchemyMonitor(BaseHTTPMiddleware):
    """Middleware for monitoring SQLAlchemy database operations.

    Tracks query execution time and counts for each request. Can trigger actions
    based on configured thresholds.

    Args:
        app: The ASGI application
        engine: SQLAlchemy engine instance (sync or async)
        actions: List of monitoring actions to execute
        allow_no_request_context: Whether to allow DB operations outside request context
    """

    request_context = ContextVar[AlchemyStatistics]("request_context", default=None)

    def __init__(
        self, app: ASGIApp, engine: Engine | AsyncEngine, actions: list[Action] = None, allow_no_request_context=False
    ):
        super().__init__(app)

        self._engine = engine if isinstance(engine, Engine) else engine.sync_engine
        self._actions = actions or []
        self._allow_no_request_context = allow_no_request_context

        event.listen(self._engine, "before_cursor_execute", self.before_cursor_execute)
        event.listen(self._engine, "after_cursor_execute", self.after_cursor_execute)

    def init_statistics(self):
        self.request_context.set(AlchemyStatistics())

    @property
    def statistics(self) -> AlchemyStatistics:
        return self.request_context.get()

    def before_cursor_execute(self, conn, cursor, statement, parameters, context, executemany):
        conn.info["query_start_time"] = time.time()

    def after_cursor_execute(self, conn, cursor, statement, parameters, context, executemany):
        total = time.time() - conn.info["query_start_time"]
        del conn.info["query_start_time"]

        if self.statistics is None:
            if not self._allow_no_request_context:
                logging.warning(
                    "Received database event without requests context. Please make sure that the "
                    "middleware is the first middleware in the stack e.g.\n"
                    "app = FastAPI()\n"
                    "app.add_middleware(SQLAlchemyMonitor, engine=engine\n"
                    "app.add_middleware(other middleware)\n\n"
                    "or if you want to allow database events without request context, "
                    "set SQLAlchemyMonitor(..., allow_no_request_context=True)"
                )

            return

        # update global stats
        self.statistics.total_invocations += 1
        self.statistics.total_invocation_time_ms += total * 1000

        # update query stats
        self.statistics.add_query_stat(query=statement, invocation_time_ms=total * 1000)

    def on_do_orm_execute(self, orm_execute_state):
        print(orm_execute_state)

    async def dispatch(self, request: Request, call_next: Callable):
        self.init_statistics()
        res = await call_next(request)

        for action in self._actions:
            action.handle(self.statistics)

        return res
