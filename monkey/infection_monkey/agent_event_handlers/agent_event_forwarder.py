import logging
import queue
import threading
from time import sleep

from common.agent_event_serializers import AgentEventSerializerRegistry
from common.agent_events import AbstractAgentEvent
from infection_monkey.island_api_client import IIslandAPIClient
from infection_monkey.utils.threading import create_daemon_thread

logger = logging.getLogger(__name__)


DEFAULT_TIME_PERIOD_SECONDS = 5


class AgentEventForwarder:
    """
    Sends information about the events carried out by the Agent to the Island in batches
    """

    def __init__(
        self,
        island_api_client: IIslandAPIClient,
        agent_event_serializer_registry: AgentEventSerializerRegistry,
    ):
        self._agent_event_serializer_registry = agent_event_serializer_registry

        self._batching_agent_event_forwarder = BatchingAgentEventForwarder(island_api_client)
        self._batching_agent_event_forwarder.start()

    def __del__(self):
        self._batching_agent_event_forwarder.stop()

    def send_event(self, event: AbstractAgentEvent):
        self._batching_agent_event_forwarder.add_event_to_queue(event)
        logger.debug(f"Sending event of type {type(event).__name__} to the Island")


class BatchingAgentEventForwarder:
    """
    Handles the batching and sending of the Agent's events to the Island
    """

    def __init__(
        self, island_api_client: IIslandAPIClient, time_period: int = DEFAULT_TIME_PERIOD_SECONDS
    ):
        self._island_api_client = island_api_client
        self._time_period = time_period

        self._queue: queue.Queue[AbstractAgentEvent] = queue.Queue()
        self._stop_batch_and_send_thread = threading.Event()

    def start(self):
        self._batch_and_send_thread = create_daemon_thread(
            target=self._manage_event_batches, name="SendEventsToIslandInBatchesThread"
        )
        self._batch_and_send_thread.start()

    def add_event_to_queue(self, serialized_event: AbstractAgentEvent):
        self._queue.put(serialized_event)

    def _manage_event_batches(self):
        while not self._stop_batch_and_send_thread.is_set():
            self._send_events_to_island()
            sleep(self._time_period)

        self._send_remaining_events()

    def _send_events_to_island(self):
        if self._queue.empty():
            return

        events = []

        while not self._queue.empty():
            events.append(self._queue.get(block=False))

        try:
            logger.debug(f"Sending Agent events to Island: {events}")
            self._island_api_client.send_events(events)
        except Exception:
            logger.exception("Exception caught when connecting to the Island")

    def _send_remaining_events(self):
        self._send_events_to_island()

    def stop(self):
        self._stop_batch_and_send_thread.set()
        self._batch_and_send_thread.join()