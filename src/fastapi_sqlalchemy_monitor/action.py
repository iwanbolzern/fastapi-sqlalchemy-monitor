"""Actions module for FastAPI SQLAlchemy Monitor.

This module provides action handlers and actions that can be triggered based on
SQLAlchemy query statistics. Actions can log, print, or raise exceptions when
certain conditions are met.
"""

import logging
from abc import ABC, abstractmethod
from dataclasses import asdict

from fastapi_sqlalchemy_monitor.statistics import AlchemyStatistics


class Action(ABC):
    """Abstract base class for monitoring actions."""

    @abstractmethod
    def handle(self, statistics: AlchemyStatistics):
        """Handle the statistics."""
        pass


class ConditionalAction(Action):
    """Base class for actions that only execute when a condition is met."""

    def handle(self, statistics: AlchemyStatistics):
        """Evaluate condition and handle if true."""
        if self._condition(statistics):
            self._handle(statistics)

    @abstractmethod
    def _condition(self, statistics: AlchemyStatistics) -> bool:
        """Evaluate if action should be taken."""
        pass

    @abstractmethod
    def _handle(self, statistics: AlchemyStatistics):
        """Handle the statistics if condition is met."""
        pass


class LogStatistics(Action):
    """Action that logs current statistics."""

    def __init__(self, log_level=logging.INFO):
        self.log_level = log_level

    def handle(self, statistics: AlchemyStatistics):
        logging.log(self.log_level, str(statistics), asdict(statistics))


class PrintStatistics(Action):
    """Action that prints current statistics."""

    def handle(self, statistics: AlchemyStatistics):
        print(str(statistics), asdict(statistics))


class MaxTotalInvocationAction(ConditionalAction):
    """Action that triggers when total query invocations exceed a threshold."""

    def __init__(self, max_invocations: int, log_level: int = None):
        self.max_invocations = max_invocations
        self.log_level = log_level

    def _condition(self, statistics: AlchemyStatistics) -> bool:
        return statistics.total_invocations > self.max_invocations

    def _handle(self, statistics: AlchemyStatistics):
        msg = f"Maximum invocations exceeded: {statistics.total_invocations} > {self.max_invocations}"
        if self.log_level is not None:
            logging.log(self.log_level, msg)
        else:
            raise ValueError(msg)


class WarnMaxTotalInvocation(MaxTotalInvocationAction):
    def __init__(self, max_invocations: int):
        super().__init__(max_invocations, logging.WARNING)


class ErrorMaxTotalInvocation(MaxTotalInvocationAction):
    def __init__(self, max_invocations: int):
        super().__init__(max_invocations, logging.ERROR)


class RaiseMaxTotalInvocation(MaxTotalInvocationAction):
    def __init__(self, max_invocations: int):
        super().__init__(max_invocations)
