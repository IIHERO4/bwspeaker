"""
Credits: IIHERO4


"""
import asyncio
import logging
from pathlib import Path
from typing import Optional, TYPE_CHECKING, cast, Dict, List

import play_sounds
import websockets

from lib.common import ConfigFile
from lib.keyboard_listener import KeyBoardListener

if TYPE_CHECKING:
    from websockets.client import WebSocketClientProtocol


# TODO add reconnection


class SpeakerClient:
    def __init__(self):
        self._worker_task = None
        self.config = ConfigFile("bwspeaker.json")
        self.mapping = ConfigFile("sounds_mapping.json")
        self.key = self.config.get_key("auth.key")
        self.listener = KeyBoardListener()
        self.server_uri = self.config.get_key("server")
        self.room_id = self.config.get_key("room_id")
        self.queue = asyncio.Queue()
        self.ws: Optional[WebSocketClientProtocol] = None

    async def run(self):

        logging.info(f"connecting to server, {self.server_uri}...")
        while True:
            try:
                self.ws: Optional[WebSocketClientProtocol] = await websockets.connect(
                    self.server_uri + ("/" if self.server_uri[-1] != "/" else "") + self.room_id
                )
                await self.ws.send(self.key)
                return_code = await asyncio.wait_for(self.ws.recv(), timeout=5)
                if return_code == "0":
                    # success
                    break

                raise PermissionError("Auth failed!")
            except Exception as e:
                logging.warning("Failed to connect", exc_info=e)
                logging.warning("Retrying in 5 seconds...")
                await asyncio.sleep(5)

        self._worker_task = asyncio.create_task(self.worker())
        self.recver_task = asyncio.create_task(self.recver())

        logging.info("connected!")

        self._load_config()

    async def worker(self):
        print("loaded worker")
        while True:
            sound_command = await self.queue.get()
            print(sound_command)
            await self.ws.send(self._get_key(sound_command))

    async def recver(self):
        while True:
            sound_key = await self.ws.recv()
            try:
                file = self.mapping[sound_key]
            except KeyError:
                logging.critical(f"bad sound key: {sound_key}")
                return
            print(" wda")
            play_sounds.play_file(Path(file), block=False)
            print("ww")

    def _get_key(self, sound_command):
        for entry in self.mapping.items():
            if entry[1] == sound_command:
                return entry[0]

    def _load_config(self):

        for hotkey in cast(List[Dict[str, str]], self.config.get_key("hotkeys")):
            logging.info(f"Registering {hotkey['name']}")
            self.listener.register_listener(
                hotkey["name"], hotkey["key"], True, lambda: self.queue.put(hotkey['sound'])
            )


async def main():
    client = SpeakerClient()
    await client.run()
    await asyncio.Future()


if __name__ == "__main__":
    # asyncio.run(main())
    asyncio.get_event_loop().run_until_complete(main())
