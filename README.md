# FastAPI SQLAlchemy Monitor

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

The middleware supports different types of actions that can be triggered based on query statistics:

- `WarnMaxTotalInvocation`: Log a warning when query count exceeds threshold
- `ErrorMaxTotalInvocation`: Log an error when query count exceeds threshold
- `RaiseMaxTotalInvocation`: Raise an exception when query count exceeds threshold
- `LogStatistics`: Log query statistics
- `PrintStatistics`: Print query statistics

### Custom Actions

The monitoring system is built on an extensible action framework. You can create custom actions by extending the `Action` class and implementing your own monitoring logic.

#### Basic Custom Action

Here's an example of a custom action that monitors average query execution time:

```python
import logging

from fastapi_sqlalchemy_monitor import AlchemyStatistics
from fastapi_sqlalchemy_monitor.action import Action, LoggingActionHandler

class AverageQueryTimeAction(Action):
    def __init__(self, threshold_ms: float):
        super().__init__(LoggingActionHandler(logging.WARNING))
        self.threshold_ms = threshold_ms

    def _evaluate(self, statistics: AlchemyStatistics) -> tuple[bool, str, dict]:
        if statistics.total_invocations == 0:
            return False, "", {}
            
        avg_time = statistics.total_invocation_time_ms / statistics.total_invocations
        if avg_time > self.threshold_ms:
            return (
                True,
                f"Average query time ({avg_time:.2f}ms) exceeds threshold ({self.threshold_ms}ms)",
                {
                    "threshold_ms": self.threshold_ms,
                    "average_time_ms": avg_time,
                    "total_queries": statistics.total_invocations
                }
            )
        return False, "", {}
```

#### Custom Action Handlers

You can also create custom action handlers by implementing the `ActionHandler` ABC:

```python
import prometheus_client

from fastapi_sqlalchemy_monitor.action import ActionHandler

class PrometheusActionHandler(ActionHandler):
    def __init__(self):
        self.query_counter = prometheus_client.Counter(
            'sql_queries_total', 
            'Total number of SQL queries executed'
        )
        
    def handle(self, msg: str, context: dict):
        self.query_counter.inc(context.get('total_queries', 1))
```

#### Combining Custom Components

Here's how to use custom actions and handlers together:

```python
# Create custom handler
metrics_handler = PrometheusActionHandler()

# Create custom action with custom handler
class QueryMetricsAction(Action):
    def __init__(self):
        super().__init__(metrics_handler)
        
    def _evaluate(self, statistics: AlchemyStatistics) -> tuple[bool, str, dict]:
        return True, "Updating metrics", {
            "total_queries": statistics.total_invocations,
            "total_time_ms": statistics.total_invocation_time_ms
        }

# Use in FastAPI app
app.add_middleware(
    SQLAlchemyMonitor,
    engine=engine,
    actions=[
        QueryMetricsAction(),
        AverageQueryTimeAction(threshold_ms=100)
    ]
)
```

#### Available Statistics

When implementing `_evaluate()`, you have access to these statistics properties:

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
3. Include relevant context in the return tuple for debugging
4. Consider performance impact of complex evaluations
5. Use type hints for better code maintenance

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
