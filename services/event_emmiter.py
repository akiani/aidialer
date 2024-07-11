import asyncio
from typing import Any, Callable, Dict, List


class EventEmitter:
    """
    A class that represents an event emitter.

    An event emitter allows registering callbacks for specific events and emitting those events
    with optional arguments and keyword arguments.
    """

    def __init__(self):
        """
        Initializes an instance of the EventEmitter class.
        """
        self._events: Dict[str, List[Callable]] = {}

    def on(self, event: str, callback: Callable):
        """
        Registers a callback for a specific event.

        Args:
            event (str): The name of the event.
            callback (Callable): The callback function to be executed when the event is emitted.
        """
        if event not in self._events:
            self._events[event] = []
        self._events[event].append(callback)

    async def emit(self, event: str, *args: Any, **kwargs: Any):
        """
        Emits an event and executes all registered callbacks for that event.

        Args:
            event (str): The name of the event.
            *args (Any): Optional positional arguments to be passed to the callbacks.
            **kwargs (Any): Optional keyword arguments to be passed to the callbacks.
        """
        if event in self._events:
            for callback in self._events[event]:
                await self._run_callback(callback, *args, **kwargs)

    async def _run_callback(self, callback: Callable, *args: Any, **kwargs: Any):
        """
        Runs a callback function with the provided arguments.

        Args:
            callback (Callable): The callback function to be executed.
            *args (Any): Optional positional arguments to be passed to the callback.
            **kwargs (Any): Optional keyword arguments to be passed to the callback.
        """
        if asyncio.iscoroutinefunction(callback):
            await callback(*args, **kwargs)
        else:
            callback(*args, **kwargs)