"""Actions module for FastAPI SQLAlchemy Monitor.

This module provides action handlers and actions that can be triggered based on
SQLAlchemy query statistics. Actions can log, print, or raise exceptions when
certain conditions are met.
"""

import logging
from abc import ABC, abstractmethod
from dataclasses import asdict

from fastapi_sqlalchemy_monitor.statistics import AlchemyStatistics


class ActionHandler(ABC):
    """Abstract base class for handling actions.

    Defines the interface for different ways to handle action triggers, such as
    logging, printing, or raising exceptions.
    """

    @abstractmethod
    def handle(self, msg: str, context: dict):
        """Handle the action with a message and context.

        Args:
            msg: The message to handle
            context: Dictionary containing contextual information
        """
        pass


class LoggingActionHandler(ActionHandler):
    """Action handler that logs messages using Python's logging module.

    Args:
        log_level: The logging level to use (e.g., logging.INFO)
    """

    def __init__(self, log_level: int):
        self.log_level = log_level

    def handle(self, msg: str, context: dict):
        """Log the message with the specified log level."""
        logging.log(self.log_level, msg, context)


class PrintActionHandler(ActionHandler):
    """Action handler that prints messages to stdout."""

    def handle(self, msg: str, context: dict):
        """Print the message and context to stdout."""
        print(msg, context)


class RaiseActionHandler(ActionHandler):
    """Action handler that raises exceptions."""

    def handle(self, msg: str, context: dict):
        """Raise a ValueError with the provided message."""
        raise ValueError(msg)


class Action(ABC):
    """Abstract base class for monitoring actions.

    Defines the interface for actions that can be evaluated against statistics.

    Args:
        handler: The ActionHandler to use when the action is triggered
    """

    def __init__(self, handler: ActionHandler):
        self.handler = handler

    def evaluate(self, statistics: AlchemyStatistics):
        """Evaluate statistics and trigger handler if conditions are met.

        Args:
            statistics: The AlchemyStatistics to evaluate
        """
        violate, msg, context = self._evaluate(statistics)
        if violate:
            self.handler.handle(msg, context)

    @abstractmethod
    def _evaluate(self, statistics: AlchemyStatistics) -> tuple[bool, str, dict]:
        """Evaluate statistics and return violation status, message and context.

        Args:
            statistics: The AlchemyStatistics to evaluate

        Returns:
            Tuple of (violation occurred, message, context dictionary)
        """
        pass


class MaxTotalInvocationAction(Action):
    """Action that triggers when total query invocations exceed a threshold.

    Args:
        max_invocations: Maximum number of query invocations allowed
        handler: The ActionHandler to use when threshold is exceeded
    """

    def __init__(self, max_invocations: int, handler: ActionHandler):
        super().__init__(handler)
        self.max_invocations = max_invocations

    def _evaluate(self, statistics: AlchemyStatistics) -> tuple[bool, str, dict]:
        """Check if total invocations exceed the maximum allowed."""
        if statistics.total_invocations > self.max_invocations:
            return (
                True,
                f"Maximum invocations exceeded: {statistics.total_invocations} > {self.max_invocations}",
                {"max_invocations": self.max_invocations, "current_invocations": statistics.total_invocations},
            )
        return False, "", {}


class WarnMaxTotalInvocation(MaxTotalInvocationAction):
    """Logs a warning when query invocations exceed threshold.

    Args:
        max_invocations: Maximum number of query invocations allowed
    """

    def __init__(self, max_invocations: int):
        super().__init__(max_invocations, LoggingActionHandler(logging.WARNING))


class ErrorMaxTotalInvocation(MaxTotalInvocationAction):
    """Logs an error when query invocations exceed threshold.

    Args:
        max_invocations: Maximum number of query invocations allowed
    """

    def __init__(self, max_invocations: int):
        super().__init__(max_invocations, LoggingActionHandler(logging.ERROR))


class RaiseMaxTotalInvocation(MaxTotalInvocationAction):
    """Raises an exception when query invocations exceed threshold.

    Args:
        max_invocations: Maximum number of query invocations allowed
    """

    def __init__(self, max_invocations: int):
        super().__init__(max_invocations, RaiseActionHandler())


class LogStatistics(Action):
    """Action that logs current statistics.

    Args:
        log_level: The logging level to use (default: logging.INFO)
    """

    def __init__(self, log_level=logging.INFO):
        super().__init__(LoggingActionHandler(log_level=log_level))

    def _evaluate(self, statistics: AlchemyStatistics) -> tuple[bool, str, dict]:
        """Always returns True to log statistics."""
        return True, str(statistics), asdict(statistics)


class PrintStatistics(Action):
    """Action that prints current statistics to stdout."""

    def __init__(self):
        super().__init__(PrintActionHandler())

    def _evaluate(self, statistics: AlchemyStatistics) -> tuple[bool, str, dict]:
        """Always returns True to print statistics."""
        return True, str(statistics), asdict(statistics)
