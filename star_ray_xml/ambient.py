"""TODO"""

from typing import List, Dict, Any
from star_ray import Ambient, Agent
from star_ray.event import ActiveObservation, ErrorActiveObservation
from star_ray.pubsub import Subscribe, Unsubscribe

from .state import XMLState, _XMLState
from .query import Select, XMLQuery

DEFAULT_XML = "<xml></xml>"
DEFAULT_NAMESPACES = {}


class XMLAmbient(Ambient):
    def __init__(
        self,
        agents: List[Agent],
        xml: str | None = None,
        namespaces: Dict[str, str] | None = None,
        xml_state: XMLState | None = None,
        **kwargs: Dict[str, Any],
    ):
        super().__init__(agents)
        self._state = None
        if xml_state is None:
            self._state = _XMLState(
                xml if xml else DEFAULT_XML,
                namespaces=namespaces if namespaces else DEFAULT_NAMESPACES,
            )
        else:
            assert xml is None  # set these directly on the `xml_state`
            assert namespaces is None  # set these directly on the `xml_state`
            self._state = xml_state

    def get_state(self) -> XMLState:
        return self._state  # NOTE: this is read only!

    def __select__(
        self, action: XMLQuery | Subscribe | Unsubscribe
    ) -> ActiveObservation | ErrorActiveObservation:
        try:
            if isinstance(action, Select):
                values = action.__execute__(self._state)
                if values is not None:
                    return ActiveObservation(action_id=action, values=values)
            elif isinstance(action, (Subscribe, Unsubscribe)):
                return self.__subscribe__(action)
            else:
                raise ValueError(
                    f"{action} does not derive from one of required type(s):`{[Select, Subscribe, Unsubscribe]}`"
                )
        except Exception as e:
            return ErrorActiveObservation.from_exception(action=action, exception=e)

    def __update__(
        self, action: XMLQuery
    ) -> ActiveObservation | ErrorActiveObservation:
        try:
            values = action.__execute__(self._state)
            if values is not None:
                return ActiveObservation(action_id=action, values=values)
        except Exception as e:
            return ErrorActiveObservation.from_exception(action, e)

    def __subscribe__(
        self, action: Subscribe | Unsubscribe
    ) -> ActiveObservation | ErrorActiveObservation:
        try:
            pass

        except Exception as e:
            return ErrorActiveObservation.from_exception(action, e)

        # try:
        #     # TODO check that the topic is one of the events that the state will publish...
        #     if isinstance(action, Subscribe):
        #         self._state.subscribe(action.topic, action.subscriber)
        #     elif isinstance(action, Unsubscribe):
        #         self._state.unsubscribe(action.topic, action.subscriber)
        #     else:
        #         raise TypeError(
        #             f"Invalid type: {type(action)}, must derive {Subscribe.__name__} or {Unsubscribe.__name__}"
        #         )
        # except Exception as e:
        #     return ErrorActiveObservation.from_exception(action, e)
