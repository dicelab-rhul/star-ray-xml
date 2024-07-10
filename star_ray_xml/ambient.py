""" TODO """

from typing import List, Dict
from star_ray import Ambient, Agent
from star_ray.event import ActiveObservation, ErrorActiveObservation
from star_ray.pubsub import Subscribe, Unsubscribe

from .state import XMLState
from .query import Select, Update, Insert, Delete, Replace, XMLQuery

DEFAULT_XML = "<xml></xml>"
DEFAULT_NAMESPACES = {}


class XMLAmbient(Ambient):

    def __init__(
        self, agents: List[Agent], xml: str = None, namespaces: Dict[str, str] = None
    ):
        super().__init__(agents)
        self._state = XMLState(
            xml if xml else DEFAULT_XML,
            namespaces=namespaces if namespaces else DEFAULT_NAMESPACES,
        )

    def get_state(self) -> XMLState:
        return self._state  # NOTE: this is read only!

    def __select__(
        self, action: XMLQuery
    ) -> ActiveObservation | ErrorActiveObservation:
        try:
            # TODO could allow others...
            if isinstance(action, Select):
                values = self._state.select(action)
                return ActiveObservation(action_id=action, values=values)
            elif isinstance(action, (Subscribe, Unsubscribe)):
                return self.__subscribe__(action)
            else:
                raise ValueError(
                    f"{action} does not derive from one of required type(s):`{[Select, Subscribe, Unsubscribe]}`"
                )
        except Exception as e:
            return ErrorActiveObservation(action_id=action, exception=e)

    def __update__(
        self, action: XMLQuery
    ) -> ActiveObservation | ErrorActiveObservation:
        try:
            values = action.__execute__(self._state)
            if not values is None:
                return ActiveObservation(action_id=action, values=values)
        except Exception as e:
            return ErrorActiveObservation.from_exception(action, e)

    def __subscribe__(
        self, action: Subscribe | Unsubscribe
    ) -> ActiveObservation | ErrorActiveObservation:
        try:
            # TODO check that the topic is one of the events that the state will publish...
            if isinstance(action, Subscribe):
                self._state.subscribe(action.topic, action.subscriber)
            elif isinstance(action, Unsubscribe):
                self._state.unsubscribe(action.topic, action.subscriber)
            else:
                raise TypeError(
                    f"Invalid type: {type(action)}, must derive {Subscribe.__name__} or {Unsubscribe.__name__}"
                )
        except Exception as e:
            return ErrorActiveObservation.from_exception(action, e)
