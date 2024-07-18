"""Defines the `XMLSensor` class which is a useful sensor implementation for observing XML related data."""

from star_ray.agent import Agent, Sensor, attempt
from star_ray.pubsub import Subscribe
from .query import select, Select, XMLQuery


class XMLSensor(Sensor):
    """Sensor that will observe all changes to an XMLAmbient. It subscribes to receive all events that subclass `XMLQuery` and initially attempts to sense all XML data (as XML source code)."""

    def __init__(self, *args, **kwargs):
        """Constructor."""
        super().__init__(*args, **kwargs)
        self._subscriptions = (XMLQuery,)

    @attempt
    def select_all(self) -> Select:
        """An attempt method that takes an action to select all current xml data.

        Returns:
            Select: the action
        """
        action = select("/*")  # select all xml data
        return action

    @attempt
    def element_exists(self, element_id: str) -> Select:
        """An attempt method that selects the `id` attribute from a given element. The `id` will match `element_id` if it is found. This can be used to check whether an element exists (if resulting observation is non-empty).

        Args:
            element_id (str): the elemnet to check.

        Returns:
            Select: the action
        """
        return select(f"//*[@id='{element_id}']", ["id"])

    def on_add(self, agent: Agent) -> None:  # noqa: D102
        super().on_add(agent)
        # initially get all xml data - this will be avaliable on the first sense cycle
        self.select_all()

    def __subscribe__(self) -> list[Subscribe]:  # noqa: D105
        return [Subscribe(topic=sub) for sub in self._subscriptions]
