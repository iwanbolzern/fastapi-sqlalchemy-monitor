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
        engine_factory: Factory function to get SQLAlchemy engine instance (sync or async). Use this if SQLAlchemy
        engine is not available at the time of middleware initialization
        actions: List of monitoring actions to execute
        allow_no_request_context: Whether to allow DB operations outside request context
    """

    request_context = ContextVar[AlchemyStatistics]("request_context", default=None)

    def __init__(
        self,
        app: ASGIApp,
        engine: Engine | AsyncEngine = None,
        engine_factory: Callable[[], Engine | AsyncEngine] = None,
        actions: list[Action] = None,
        allow_no_request_context=False,
    ):
        super().__init__(app)

        if engine is None and engine_factory is None:
            raise ValueError("SQLAlchemyMonitor middleware requires either engine or engine_factory")

        if engine and engine_factory:
            raise ValueError("SQLAlchemyMonitor middleware requires either engine or engine_factory, not both")

        self._actions = actions or []
        self._allow_no_request_context = allow_no_request_context
        self._engine = None
        self._engine_factory = engine_factory

        if engine:
            self._engine = self._register_listener(engine)

    def init_statistics(self):
        self.request_context.set(AlchemyStatistics())

    @property
    def statistics(self) -> AlchemyStatistics:
        return self.request_context.get()

    def before_cursor_execute(self, conn, cursor, statement, parameters, context, executemany):
        conn.info["query_start_time"] = time.time()

    def after_cursor_execute(self, conn, cursor, statement, parameters, context, executemany):
        query_start_time = conn.info.pop("query_start_time", None)
        if query_start_time is None:
            logging.warning("Received after_cursor_execute event without before_cursor_execute event")
            return

        total = time.time() - query_start_time

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
        if self._engine_factory is None:
            return await self._dispatch(request, call_next)

        engine = self._register_listener(self._engine_factory())

        res = await self._dispatch(request, call_next)

        event.remove(engine, "before_cursor_execute", self.before_cursor_execute)
        event.remove(engine, "after_cursor_execute", self.after_cursor_execute)

        return res

    async def _dispatch(self, request: Request, call_next: Callable):
        self.init_statistics()
        res = await call_next(request)

        for action in self._actions:
            action.handle(self.statistics)

        return res

    def _register_listener(self, engine: Engine | AsyncEngine) -> Engine:
        if isinstance(engine, AsyncEngine):
            engine = engine.sync_engine

        event.listen(engine, "before_cursor_execute", self.before_cursor_execute)
        event.listen(engine, "after_cursor_execute", self.after_cursor_execute)

        return engine
