import asyncio
import logging
from typing import Dict, List

import websockets

from lib.common import ConfigFile
from websockets.legacy.client import WebSocketClientProtocol


class Room:
    def __init__(self, server: "SpeakerServer"):
        self.server = server
        self.members: List[WebSocketClientProtocol] = []

    async def broadcast(self, key):
        print("Broadcasting " + key)
        for ws in self.members:
            await ws.send(key)

    def add(self, ws):
        self.members.append(ws)

    def remove(self, ws):
        self.members.remove(ws)

class ClientInfo:
    def __init__(self, ws: WebSocketClientProtocol, room_id: str):
        self.ws = ws
        self.room = room_id

class SpeakerServer:
    def __init__(self):
        self.config = ConfigFile("server_config.json")
        self.rooms_info: Dict[str, List[str]] = self.config.get_key("rooms")
        self.rooms: Dict[str, Room] = {rid: Room(self) for rid in self.rooms_info}
        self.connected: Dict[str, ClientInfo] = {}

    async def run(self):
        port = self.config.get_key("port")
        uri = self.config.get_key("uri")
        async with websockets.serve(self.on_connection, uri, port) as ws:
            logging.info(f"Serving to {uri}:{port}")
            await asyncio.Future()

    async def on_connection(self, ws: WebSocketClientProtocol, path: str):
        logging.info(f"--- New Connection ---")
        logging.info(f"WS: {ws.remote_address} {ws.local_address}, path: {path}")
        room_id = path[1:]

        if room_id not in self.rooms_info:
            try:
                await asyncio.wait_for(ws.send("404"), timeout=5)
            except asyncio.TimeoutError:
                pass

            return

        try:
            key = await asyncio.wait_for(ws.recv(), timeout=5)
        except asyncio.TimeoutError:
            return

        if key not in self.rooms_info[room_id]:
            try:
                await asyncio.wait_for(ws.send("403"), timeout=5)
            except asyncio.TimeoutError:
                return

        await ws.send("0")

        room = self.rooms[room_id]
        room.add(ws)
        try:
            while True:
                key = await ws.recv()
                await room.broadcast(key)
        except Exception:
            room.remove(ws)
        print()


async def main():
    server = SpeakerServer()
    await server.run()


if __name__ == "__main__":
    # asyncio.run(main())
    asyncio.get_event_loop().run_until_complete(main())
