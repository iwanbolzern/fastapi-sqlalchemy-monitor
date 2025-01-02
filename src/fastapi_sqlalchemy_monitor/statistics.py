from dataclasses import dataclass, field


@dataclass
class QueryStatistic:
    """Statistics for a single SQL query.

    Tracks execution count and timing information for a specific SQL query.
    """

    query: str  # The query that was executed
    total_invocations: int = 0  # The total number of invocations of this query
    total_invocation_time_ms: int = 0  # The total time (ms) spent waiting for the database to respond
    invocation_times_ms: list[int] = field(
        default_factory=lambda: []
    )  # The time (ms) spent waiting for the database to respond for each invocation of this query


@dataclass
class AlchemyStatistics:
    """Aggregates statistics for all SQL queries during a request.

    Maintains counters for total query executions and timing, plus detailed stats per query.
    """

    total_invocations: int = 0  # Total number of invocations cline <---> database round trips
    total_invocation_time_ms: int = 0  # Total time (ms) spent waiting for the database to respond
    query_stats: dict[str, QueryStatistic] = field(default_factory=lambda: {})  # The statistics for each query

    def add_query_stat(self, query: str, invocation_time_ms: int):
        query_hash = hash(query)
        query_stat = self.query_stats.get(query_hash, None)
        if query_stat is None:
            query_stat = QueryStatistic(
                query=query,
            )
            self.query_stats[query_hash] = query_stat

        query_stat.total_invocations += 1
        query_stat.total_invocation_time_ms += invocation_time_ms
        query_stat.invocation_times_ms.append(invocation_time_ms)

    def __str__(self):
        return f"Total invocations: {self.total_invocations}, total invocation time: {self.total_invocation_time_ms} ms"
