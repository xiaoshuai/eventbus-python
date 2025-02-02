import asyncio

from event_bus import EventBus, EventBusAsyncIO


def event_bus_demo():
    def event_handler():
        print("BANG BANG")

    eb = EventBus()
    print("event_a")
    eb.add_listener("event_a", event_handler)
    eb.emit("event_a")
    eb.emit("event_a")
    eb.remove_listener("event_a", event_handler)
    eb.emit("event_a")
    print("event_b")
    eb.add_once_listener("event_b", event_handler)
    eb.emit("event_b")
    eb.emit("event_b")
    eb.remove_listener("event_b", event_handler)
    eb.emit("event_b")


async def event_bus_asyncio_demo():
    async def async_callback():
        await asyncio.sleep(1)
        print("BANG BANG")
        await asyncio.sleep(1)
        raise ValueError("Something went wrong!")

    async def error_handler(err):
        print(f"Caught an error: {err}")

    eb = EventBusAsyncIO()
    print("event_a")
    eb.add_listener("event_a", async_callback)
    eb.add_listener("error", error_handler)
    eb.emit("event_a")
    eb.emit("event_a")
    eb.remove_listener("event_a", async_callback)
    eb.emit("event_a")
    print("event_b")
    eb.add_once_listener("event_b", async_callback)
    eb.emit("event_b")
    eb.emit("event_b")
    eb.remove_listener("event_b", async_callback)
    eb.emit("event_b")

    await asyncio.sleep(1)
    print(f"has_pending_tasks {eb.has_pending_tasks()}")
    print(f"cancel_all {eb.cancel_all()}")
    print(f"has_pending_tasks {eb.has_pending_tasks()}")
    await asyncio.sleep(3)


if __name__ == "__main__":
    print("## event_bus_demo")
    event_bus_demo()
    print("## event_bus_asyncio_demo")
    asyncio.run(event_bus_asyncio_demo())
