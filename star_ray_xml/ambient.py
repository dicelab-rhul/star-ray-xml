import asyncio
from typing import List, Dict
from star_ray import Ambient, Agent
from star_ray.event import ActiveObservation, ErrorActiveObservation
from star_ray.pubsub import Subscribe, Unsubscribe, EventPublisher

from .state import XMLState
from .query import Select, Update, Insert, Delete, Replace, XPathQuery

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
        self, action: XPathQuery
    ) -> ActiveObservation | ErrorActiveObservation:
        try:
            if isinstance(action, Select):
                values = self._state.select(action)
                return ActiveObservation(action_id=action, values=values)
            else:
                raise ValueError(
                    f"{action} does not derive from one of required type(s) `[{Select.__name__}]`"
                )
        except Exception as e:
            return ErrorActiveObservation(action_id=action, exception=e)

    def __update__(
        self, action: XPathQuery
    ) -> ActiveObservation | ErrorActiveObservation:
        try:
            values = None
            if isinstance(action, Update):
                values = self._state.update(action)
            elif isinstance(action, Insert):
                values = self._state.insert(action)
            elif isinstance(action, Delete):
                values = self._state.delete(action)
            elif isinstance(action, Replace):
                values = self._state.replace(action)
            elif hasattr(action, "execute"):
                values = action.execute(
                    self._state
                )  # this will execute the action using the execute API
            else:
                raise ValueError(
                    f"{action} does not derive from one of required type(s) `[{Update.__name__}, {Insert.__name__}, {Delete.__name__}. {Replace.__name__}]`"
                )
            return ActiveObservation(action_id=action, values=values)
        except Exception as e:
            return ErrorActiveObservation(action_id=action, exception=e)

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
            return ErrorActiveObservation(action_id=action, exception=e)
