# -*- coding: utf-8 -*-
import asyncio
from asyncio import AbstractEventLoop, Future, iscoroutine, ensure_future
from collections import OrderedDict
from threading import Lock
from typing import (
    Any,
    Callable,
    Dict,
    List,
    Mapping,
    Optional,
    Set,
    TypeVar, Tuple, cast,
)


class EventBusError(Exception):
    pass


Handler = TypeVar("Handler", bound=Callable)


class EventBus:
    def __init__(self) -> None:
        self._events: Dict[
            str,
            "OrderedDict[Callable, Callable]",
        ] = dict()
        self._lock: Lock = Lock()

    def __getstate__(self) -> Mapping[str, Any]:
        state = self.__dict__.copy()
        del state["_lock"]
        return state

    def __setstate__(self, state: Mapping[str, Any]) -> None:
        self.__dict__.update(state)
        self._lock = Lock()

    def add_listener(self, event: str, f: Handler) -> None:
        self.emit("new_listener", event, f)
        with self._lock:
            if event not in self._events:
                self._events[event] = OrderedDict()
            self._events[event][f] = f

    def add_once_listener(self, event: str, f: Handler) -> None:
        def wrapper(*args: Any, **kwargs: Any) -> None:
            self._emit_run(f, args, kwargs)
            with self._lock:
                if event in self._events and wrapper in self._events[event]:
                    self._events[event].pop(wrapper)
                    if not len(self._events[event]):
                        del self._events[event]

        self.add_listener(event, wrapper)

    def event_names(self) -> Set[str]:
        return set(self._events.keys())

    def emit(
            self,
            event: str,
            *args: Any,
            **kwargs: Any,
    ) -> bool:
        handled = False
        with self._lock:
            funcs = list(self._events.get(event, OrderedDict()).values())
        for f in funcs:
            self._emit_run(f, args, kwargs)
            handled = True

        if not handled:
            error: Any = args[0] if args else None
            if event == "error":
                if isinstance(error, Exception):
                    raise error
                else:
                    raise EventBusError(f"未捕获的未指定错误事件: {error}")

        return handled

    def remove_listener(self, event: str, f: Callable) -> None:
        with self._lock:
            if event in self._events and f in self._events[event]:
                self._events[event].pop(f)
                if not len(self._events[event]):
                    del self._events[event]

    def remove_all_listeners(self, event: Optional[str] = None) -> None:
        with self._lock:
            if event is not None:
                self._events[event] = OrderedDict()
            else:
                self._events = dict()

    def listeners(self, event: str) -> List[Callable]:
        return list(self._events.get(event, OrderedDict()).keys())

    def _emit_run(self, f, args, kwargs):
        f(*args, **kwargs)


class EventBusAsyncIO(EventBus):
    def __init__(self, loop: Optional[AbstractEventLoop] = None):
        super(EventBusAsyncIO, self).__init__()
        self._loop: Optional[AbstractEventLoop] = loop
        self._waiting: Set[Future] = set()

    def _emit_run(
            self,
            f: Callable,
            args: Tuple[Any, ...],
            kwargs: Dict[str, Any],
    ):
        try:
            coro: Any = f(*args, **kwargs)
        except Exception as exc:
            self.emit("error", exc)
        else:
            if iscoroutine(coro):
                if self._loop:
                    fut: Any = ensure_future(cast(Any, coro), loop=self._loop)
                else:
                    fut = ensure_future(cast(Any, coro))
            elif isinstance(coro, Future):
                fut = cast(Any, coro)
            else:
                return

            def callback(f):
                self._waiting.discard(f)
                if f.cancelled():
                    return
                exc: Exception = f.exception()
                if exc:
                    self.emit("error", exc)

            fut.add_done_callback(callback)
            self._waiting.add(fut)

    async def wait_for_all(self):
        if self._waiting:
            await asyncio.wait(self._waiting)

    def cancel_all(self):
        for fut in self._waiting:
            if not fut.done() and not fut.cancelled():
                fut.cancel()
        self._waiting.clear()

    def has_pending_tasks(self) -> bool:
        return bool(self._waiting)
