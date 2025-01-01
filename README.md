# FastAPI SQLAlchemy Monitor

[![PyPI version](https://badge.fury.io/py/fastapi-sqlalchemy-monitor.svg)](https://badge.fury.io/py/fastapi-sqlalchemy-monitor)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Test](https://github.com/iwanbolzern/fastapi-sqlalchemy-monitor/actions/workflows/test.yml/badge.svg)](https://github.com/iwanbolzern/fastapi-sqlalchemy-monitor/actions/workflows/test.yml)
[![Python Versions](https://img.shields.io/pypi/pyversions/fastapi-sqlalchemy-monitor.svg)](https://pypi.org/project/fastapi-sqlalchemy-monitor/)

A middleware for FastAPI that monitors SQLAlchemy database queries, providing insights into database usage patterns and helping catch potential performance issues.

## Features

- 📊 Track total database query invocations and execution times
- 🔍 Detailed per-query statistics
- ⚡ Async support
- 🎯 Configurable actions for monitoring and alerting
- 🛡️ Built-in protection against N+1 query problems

## Installation

```bash
pip install fastapi-sqlalchemy-monitor
```

## Quick Start

```python
from fastapi import FastAPI
from sqlalchemy import create_engine

from fastapi_sqlalchemy_monitor import SQLAlchemyMonitor
from fastapi_sqlalchemy_monitor.action import WarnMaxTotalInvocation, PrintStatistics

# Create async engine
engine = create_engine("sqlite:///./test.db")

app = FastAPI()

# Add the middleware with actions
app.add_middleware(
    SQLAlchemyMonitor,
    engine=engine,
    actions=[
        WarnMaxTotalInvocation(max_invocations=10),  # Warn if too many queries
        PrintStatistics()  # Print statistics after each request
    ]
)
```

## Actions

The middleware supports different types of actions that can be triggered based on query statistics.

### Built-in Actions

- `WarnMaxTotalInvocation`: Log a warning when query count exceeds threshold
- `ErrorMaxTotalInvocation`: Log an error when query count exceeds threshold
- `RaiseMaxTotalInvocation`: Raise an exception when query count exceeds threshold
- `LogStatistics`: Log query statistics
- `PrintStatistics`: Print query statistics

### Custom Actions

The middleware provides two interfaces for implementing custom actions:

- `Action`: Simple interface that executes after every request
- `ConditionalAction`: Advanced interface that executes only when specific conditions are met

#### Basic Custom Action

Here's an example of a custom action that records Prometheus metrics:

```python
from prometheus_client import Counter

from fastapi_sqlalchemy_monitor import AlchemyStatistics
from fastapi_sqlalchemy_monitor.action import Action

class PrometheusAction(Action):
    def __init__(self):
        self.query_counter = Counter(
            'sql_queries_total', 
            'Total number of SQL queries executed'
        )
        
    def handle(self, statistics: AlchemyStatistics):
        self.query_counter.inc(statistics.total_invocations)
```

#### Conditional Action Example

Here's an example of a conditional action that monitors for slow queries:

```python
import logging

from fastapi_sqlalchemy_monitor import AlchemyStatistics
from fastapi_sqlalchemy_monitor.action import ConditionalAction

class SlowQueryMonitor(ConditionalAction):
    def __init__(self, threshold_ms: float):
        self.threshold_ms = threshold_ms

    def _condition(self, statistics: AlchemyStatistics) -> bool:
        # Check if any query exceeds the time threshold
        return any(
            query.total_invocation_time_ms > self.threshold_ms 
            for query in statistics.query_stats.values()
        )

    def _handle(self, statistics: AlchemyStatistics):
        # Log details of slow queries
        for query_stat in statistics.query_stats.values():
            if query_stat.total_invocation_time_ms > self.threshold_ms:
                logging.warning(
                    f"Slow query detected ({query_stat.total_invocation_time_ms:.2f}ms): "
                    f"{query_stat.query}"
                )
```

#### Using Custom Actions

Here's how to use custom actions:

```python
app.add_middleware(
    SQLAlchemyMonitor,
    engine=engine,
    actions=[
        PrometheusAction(),
        SlowQueryMonitor(threshold_ms=100)
    ]
)
```

#### Available Statistics

When implementing custom actions, you have access to these statistics properties:

- `statistics.total_invocations`: Total number of queries executed
- `statistics.total_invocation_time_ms`: Total execution time in milliseconds
- `statistics.query_stats`: Dictionary of per-query statistics

Each `QueryStatistic` in `query_stats` contains:
- `query`: The SQL query string
- `total_invocations`: Number of times this query was executed
- `total_invocation_time_ms`: Total execution time for this query
- `invocation_times_ms`: List of individual execution times

#### Best Practices

1. Keep actions focused on a single responsibility
2. Use appropriate log levels for different severity conditions
3. Consider performance impact of complex evaluations
4. Use type hints for better code maintenance

## Example with Async SQLAlchemy

```python
from fastapi import FastAPI
from sqlalchemy.ext.asyncio import create_async_engine

from fastapi_sqlalchemy_monitor import SQLAlchemyMonitor
from fastapi_sqlalchemy_monitor.action import PrintStatistics

# Create async engine
engine = create_async_engine("sqlite+aiosqlite:///./test.db")

app = FastAPI()

# Add middleware
app.add_middleware(
    SQLAlchemyMonitor,
    engine=engine,
    actions=[PrintStatistics()]
)
```

## Contributing

Contributions are welcome! Please feel free to submit a Pull Request.

## License

This project is licensed under the MIT License.
