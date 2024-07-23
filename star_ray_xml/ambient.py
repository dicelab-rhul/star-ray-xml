"""Contains the default `Ambient` (see `star_ray`) implementation that uses XML as its state description language and xpath as its query language."""

from typing import Any
from star_ray import Ambient, Agent
from star_ray.event import ActiveObservation, ErrorActiveObservation
from star_ray.pubsub import Subscribe, Unsubscribe

from .state import XMLState, _XMLState
from .query import Select, XMLQuery

DEFAULT_XML = "<xml></xml>"
DEFAULT_NAMESPACES = {}


class XMLAmbient(Ambient):
    """An implementation of an `Ambient` (see `star_ray`) that uses XML as its state description language and xpath as its query language."""

    def __init__(
        self,
        agents: list[Agent],
        xml: str | None = None,
        namespaces: dict[str, str] | None = None,
        xml_state: XMLState | None = None,
        **kwargs: dict[str, Any],
    ):
        """Constructor.

        Args:
            agents (list[Agent]): list of agents to add to this `Ambient` initially.
            xml (str | None, optional): initial xml data. Defaults to <xml></xml>.
            namespaces (dict[str, str], optional): namespace map associated with the initial `xml` data. Defaults to an empty dict.
            xml_state (XMLState | None, optional): XMLState to use as the underlying state. Defaults to using `star_ray_xml._XMLState` with the arguments `xml` and `namespaces` as provided.
            kwargs (dict[str, Any]): Additional optional arguments.
        """
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
        """Get the underlying `XMLState`, this should be read only and NEVER modified without a call to `__update__` to prevent unexpected issues.

        Returns:
            XMLState: the current state of this `Ambient`.
        """
        return self._state  # NOTE: this is read only!

    def __select__(
        self, action: XMLQuery | Subscribe | Unsubscribe
    ) -> ActiveObservation | ErrorActiveObservation:
        """Execute a read-only action in this `Ambient`. These actions must derive `XMLQuery` or be a subscription action to avoid an unknown action error.

        Args:
            action (XMLQuery | Subscribe | Unsubscribe): action to execute

        Raises:
            ValueError: if the action type is unknown.

        Returns:
            ActiveObservation | ErrorActiveObservation: the resulting observation.
        """
        try:
            if isinstance(action, XMLQuery) and action.is_read:
                values = action.__execute__(self._state)
                if (
                    values is not None
                ):  # TODO typically the result wont be None... perhaps something has gone wrong if it does?
                    return ActiveObservation(action_id=action, values=values)
            elif isinstance(action, Subscribe | Unsubscribe):
                return self.__subscribe__(action)
            else:
                raise ValueError(
                    f"{action} does not derive from one of required type(s):`{[Select, Subscribe, Unsubscribe]}`"
                )
        except Exception as e:
            return ErrorActiveObservation.from_exception(action=action, exception=e)

    def __update__(
        self, action: XMLQuery
    ) -> ActiveObservation | ErrorActiveObservation | None:
        """Execute a write action in this `Ambient`. These actions must derive `XMLQuery` to avoid an unknown action error.

        Args:
            action (XMLQuery): the action to execute.

        Returns:
            ActiveObservation | ErrorActiveObservation | None: the resulting observation
        """
        try:
            values = action.__execute__(self._state)
            if values is not None:
                return ActiveObservation(action_id=action, values=values)
        except Exception as e:
            return ErrorActiveObservation.from_exception(action, e)

    def __subscribe__(  # TODO perhaps this should be supported... why isn't it?
        self, action: Subscribe | Unsubscribe
    ) -> ActiveObservation | ErrorActiveObservation:
        """Subscribe to receive events from this ambient. THIS IS NOT SUPPORTED by `XMLAmbient`. If you wish to subscribe to receive XML related events subclass `XMLAmbient` and implement publishing of actions.

        Args:
            action (Subscribe | Unsubscribe): action to execute

        Raises:
            ValueError: if this method is called, it is not a supported operation.

        Returns:
            ActiveObservation | ErrorActiveObservation: _description_
        """
        try:
            raise ValueError(
                f"`star_ray` pub-sub is not supported by ambient of type: `{XMLAmbient}`."
            )
        except Exception as e:
            return ErrorActiveObservation.from_exception(action, e)
