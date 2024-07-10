from typing import Type, Tuple
from star_ray.agent import Agent, Sensor, attempt
from star_ray.event import Action
from star_ray.pubsub import Subscribe
from .query import select, Update, Insert, Replace, Delete


class XMLSensor(Sensor):

    def __init__(self, *args, subscriptions: Tuple[Type[Action]] = None, **kwargs):
        super().__init__(*args, **kwargs)
        self._subscriptions = (
            subscriptions if subscriptions else (
                Update, Insert, Replace, Delete)
        )

    @attempt
    def select_all(self):
        return select(xpath="/*")  # select all xml data

    @attempt
    def element_exists(self, element_id: str):
        return select(xpath=f"//*[@id='{element_id}']", attrs=["id"])

    def on_add(self, agent: Agent) -> None:
        super().on_add(agent)
        # initially get all xml data - this will be avaliable on the first sense cycle
        self.select_all()

    def __subscribe__(self):
        return [Subscribe(topic=sub) for sub in self._subscriptions]
