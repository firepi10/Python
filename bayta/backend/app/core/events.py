"""In-process pub/sub bridged to Server-Sent Events.

Any mutation publishes a topic ("calendar", "photos", "meals", ...); every
connected UI (the wall kiosk, phones on the PWA) refreshes that slice live.
"""

import asyncio
import contextlib


class EventBus:
    def __init__(self) -> None:
        self._subscribers: set[asyncio.Queue[str]] = set()
        self._loop: asyncio.AbstractEventLoop | None = None

    def attach_loop(self, loop: asyncio.AbstractEventLoop) -> None:
        self._loop = loop

    def subscribe(self) -> asyncio.Queue[str]:
        q: asyncio.Queue[str] = asyncio.Queue(maxsize=64)
        self._subscribers.add(q)
        return q

    def unsubscribe(self, q: asyncio.Queue[str]) -> None:
        self._subscribers.discard(q)

    def publish(self, topic: str) -> None:
        """Thread-safe: sync jobs in the scheduler's executor publish too."""

        def _fanout() -> None:
            for q in list(self._subscribers):
                with contextlib.suppress(asyncio.QueueFull):
                    q.put_nowait(topic)

        try:
            running = asyncio.get_running_loop()
        except RuntimeError:
            running = None
        if running is not None:
            _fanout()
        elif self._loop is not None and not self._loop.is_closed():
            self._loop.call_soon_threadsafe(_fanout)


bus = EventBus()
