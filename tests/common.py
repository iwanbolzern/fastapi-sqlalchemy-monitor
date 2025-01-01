from dataclasses import asdict

from fastapi_sqlalchemy_monitor.action import Action, ActionHandler
from fastapi_sqlalchemy_monitor.statistics import AlchemyStatistics


class TestHandler(ActionHandler):
    def __init__(self):
        self.msg = None
        self.context = None

    def handle(self, msg: str, context: dict):
        self.msg = msg
        self.context = context


class TestAction(Action):
    def __init__(self):
        super().__init__(handler=TestHandler())

    def _evaluate(self, statistics: AlchemyStatistics) -> tuple[bool, str, dict]:
        return True, str(statistics), asdict(statistics)
