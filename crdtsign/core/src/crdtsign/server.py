"""Sync server implementation."""
import logging
from datetime import datetime
import os
from pathlib import Path

from hypercorn import Config
from hypercorn.asyncio import serve
from loguru import logger
from pycrdt import create_update_message
from pycrdt.store import FileYStore
from pycrdt.websocket import ASGIServer, WebsocketServer, YRoom


class ServerRoom(YRoom):
    """Implementation of the YRoom that logs updates to a persistent YStore."""

    def __init__(self, *args, **kwargs):
        """Initialize the ServerRoom instance."""
        super().__init__(*args, **kwargs)
        self._update_count = 0

    async def _broadcast_updates(self):
        """Broadcast updates with logging."""
        if self.ystore is not None:
            async with self.ystore.start_lock:
                if not self.ystore.started.is_set():
                    await self._task_group.start(self.ystore.start)

        async with self._update_receive_stream:
            async for update in self._update_receive_stream:
                if self._task_group.cancel_scope.cancel_called:
                    return

                if self.clients:
                    # broadcast update to all clients
                    message = create_update_message(update)
                    for client in self.clients:
                        try:
                            self.log.debug(f"Sending update to client with endpoint: {client.path}")
                            self._task_group.start_soon(client.send, message)
                        except Exception as e:
                            self._handle_exception(e)
                if self.ystore:
                    try:
                        self._update_count += 1
                        update_size = len(update)
                        update_time = datetime.now().isoformat()

                        self._task_group.start_soon(self.ystore.write, update)

                        self.log.info(
                            "\n"
                            f"[YStore Update #{self._update_count}]\n"
                            f"Update Time: {update_time}\n"
                            f"Update Size: {update_size} bytes\n"
                            f"Room: {getattr(self, '_room_name', 'unknown')}\n"
                            f"Active clients: {len(self.clients)}\n"
                            "\n"
                        )
                    except Exception as e:
                        self.log.exception(f"Failed to write update to YStore: {e}")
                        self._handle_exception(e)


class SyncServer(WebsocketServer):
    """Sync server implementation."""

    def __init__(self, store_directory: str, **kwargs):
        """Initialize the SyncServer instance."""
        super().__init__(**kwargs)
        self._store_directory = Path(store_directory)
        self._store_directory.mkdir(exist_ok=True)
        self._ystores = {}      # Keep track of one room per store
        self._update_count = 0

    async def get_room(self, name: str) -> YRoom:
        """Get a YRoom instance or create a new one."""
        if name not in self.rooms.keys():
            room_store_path = f"{str(self._store_directory)}/{name}_store.bin"
            room_store = FileYStore(str(room_store_path))

            self._ystores[name] = room_store

            room  = ServerRoom(
                ready=self.rooms_ready,
                ystore=room_store,
                log=self.log
            )

            room._room_name = name
            self.rooms[name] = room
            self.log.info(f"Created new room '{name}'")
        room = self.rooms[name]
        await self.start_room(room)
        return room

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Clean up all rooms on exit."""
        for room_name, ystore in self._ystores.items():
            try:
                await ystore.stop()
                self.log.info(f"Closed store for room: {room_name}")
            except Exception as e:
                self.log.error(f"Error closing store for room {room_name}: {e}")
        await super().__aexit__(exc_type, exc_val, exc_tb)

async def run_server(host: str, port: int, store_directory: str = "./.storage/sync_stores"):
    """Run the sync server asynchronously."""
    sync_server = SyncServer(store_directory=store_directory, log=logger)
    app = ASGIServer(sync_server)
    config = Config()
    config.bind = [f"{host}:{port}"]
    async with sync_server:
        await serve(app, config, mode="asgi")
