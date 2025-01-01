from fastapi_sqlalchemy_monitor.action import Action
from fastapi_sqlalchemy_monitor.statistics import AlchemyStatistics


class TestAction(Action):
    def __init__(self):
        self.statistics = None

    def handle(self, statistics: AlchemyStatistics):
        self.statistics = statistics
