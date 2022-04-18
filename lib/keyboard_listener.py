import asyncio
from typing import List, Dict, Coroutine, Callable

import keyboard

ListenerType = Callable[[], Coroutine]


class EventHandler:
    def __init__(self, is_async: bool, callback, name: str):
        self.callback = callback
        self.name = name
        self.is_async = is_async
        self._loop = asyncio.get_running_loop()

    def __call__(self, *args, **kwargs):
        if self.is_async:
            return asyncio.run_coroutine_threadsafe(self.callback(*args, **kwargs), loop=self._loop)

        return self.callback(*args, **kwargs)


class KeyBoardListener:
    def __init__(self):
        self.listeners: Dict[str, List[EventHandler]] = {}
        self.loop = asyncio.get_running_loop()

    def register_listener(self, name: str, key: str, callback: ListenerType, **options):
        """Registers a fucking listener"""
        actual = EventHandler(asyncio.iscoroutinefunction(callback), callback, name)

        try:
            self.listeners[key].append(actual)
        except KeyError:
            self.listeners[key] = [actual]

        keyboard.add_hotkey(key, actual, **options)
        return actual

    def unregister_listener(self, key: str, name: str):
        if key not in self.listeners:
            raise KeyError(f"{key} not found")

        for handler in self.listeners[key]:
            if handler.name == name:
                keyboard.remove_hotkey(handler.callback)
                return handler
