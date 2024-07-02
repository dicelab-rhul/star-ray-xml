from typing import Type, Tuple
from star_ray.agent import Sensor, attempt
from star_ray.environment import State
from star_ray.event import Action
from star_ray.pubsub import Subscribe
from .query import select, Update, Insert, Replace, Delete


class XMLSensor(Sensor):

    def __init__(self, *args, subscriptions: Tuple[Type[Action]] = None, **kwargs):
        super().__init__(*args, **kwargs)
        self._subscriptions = (
            subscriptions if subscriptions else (Update, Insert, Replace, Delete)
        )

    @attempt
    def select_all(self):
        return select(xpath="/*")  # select all xml data

    @attempt
    def element_exists(self, element_id: str):
        return select(xpath=f"//*[@id='{element_id}']", attrs=["id"])

    def __initialise__(self, state: State) -> None:
        super().__initialise__(state)
        self.select_all()  # initially get all xml data - this will be avaliable on the first sense cycle

    def __subscribe__(self):
        return [Subscribe(topic=sub) for sub in self._subscriptions]
