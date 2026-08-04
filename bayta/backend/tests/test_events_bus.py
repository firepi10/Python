import asyncio

from app.core.events import EventBus


def test_bus_fanout_and_unsubscribe():
    async def scenario():
        bus = EventBus()
        bus.attach_loop(asyncio.get_running_loop())
        q1, q2 = bus.subscribe(), bus.subscribe()
        bus.publish("calendar")
        assert await q1.get() == "calendar"
        assert await q2.get() == "calendar"
        bus.unsubscribe(q2)
        bus.publish("photos")
        assert await q1.get() == "photos"
        assert q2.empty()

    asyncio.run(scenario())
