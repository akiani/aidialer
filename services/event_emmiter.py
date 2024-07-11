import asyncio
from typing import Any, Callable, Dict, List


class EventEmitter:
    def __init__(self):
        self._events: Dict[str, List[Callable]] = {}

    def on(self, event: str, callback: Callable):
        if event not in self._events:
            self._events[event] = []
        self._events[event].append(callback)

    async def emit(self, event: str, *args: Any, **kwargs: Any):
        if event in self._events:
            for callback in self._events[event]:
                await self._run_callback(callback, *args, **kwargs)

    async def _run_callback(self, callback: Callable, *args: Any, **kwargs: Any):
        if asyncio.iscoroutinefunction(callback):
            await callback(*args, **kwargs)
        else:
            callback(*args, **kwargs)