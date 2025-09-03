"""Functions to deal with storage of signatures and user keys."""

import logging
import os
from datetime import datetime
from typing import Optional

from loguru import logger
import shortuuid
from httpx_ws import aconnect_ws
from pycrdt import Doc, Map, Provider
from pycrdt.websocket.websocket import HttpxWebsocket
from rich.console import Console
from rich.table import Table


class FileSignatureStorage:
    """Storage for file signatures using pycrdt's CRDT data structures."""

    def __init__(
        self,
        client_id: str,
        host: str,
        port: int,
        room_name: str = "file-signatures",
        from_file: bool = False,
    ):
        """Initialize a new FileSignatureStorage instance.

        Args:
            client_id: Unique identifier for this client
            host: Hostname or IP address of the server
            port: Port number of the server
            room_name: Name of the room in the server for this client
            from_file: If True, attempts to load the document state from the default
                      storage file (.storage/signatures.bin). Defaults to False.
        """
        self.client_id = client_id
        self.host = "server" if os.environ.get("IS_CONTAINER") == "true" else host
        self.port = port
        self.room_name = room_name
        self.doc = Doc()
        self.files_map = self.doc.get("files", type=Map)
        self._connected = False
        self._ws_provider = None
        self._provider_task = None

        # Load state from file if requested
        if from_file:
            self.load_signatures_from_file()

    async def _create_ws_provider(
        self,
        host,
        port,
        room_name,
        doc=None,
        log=None,
    ):
        """Create a websocket provider for connecting to the server."""
        doc = Doc() if doc is None else doc


        self._websocket = None
        self._provider = None
        self._connection_task = None

        try:
            # Create the websocket connection
            self._websocket_context = aconnect_ws(f"http://{host}:{port}/{room_name}")
            self._websocket = await self._websocket_context.__aenter__()

            # Create the provider
            self._provider_context = Provider(doc, HttpxWebsocket(self._websocket, room_name), log=log)
            self._provider = await self._provider_context.__aenter__()

            # Store contexts for cleanup
            self._contexts = [self._provider_context, self._websocket_context]

            return doc

        except Exception as e:
            logger.error(f"Error creating websocket provider: {e}")
            # Clean up any partially created resources
            await self._cleanup_provider_resources()
            raise

    async def _cleanup_provider_resources(self):
        """Clean up websocket provider resources safely."""
        import asyncio

        # Clean up contexts in reverse order
        if hasattr(self, '_contexts'):
            for context in reversed(self._contexts):
                try:
                    await context.__aexit__(None, None, None)
                except asyncio.CancelledError:
                    # Handle cancellation gracefully - don't propagate
                    logger.debug(f"[{self.room_name}] Context cleanup cancelled for client {self.client_id}")
                except Exception as e:
                    logger.debug(f"[{self.room_name}] Error cleaning up context for client {self.client_id}: {e}")
            self._contexts = []

        # Reset state
        self._websocket = None
        self._provider = None

    async def connect(self):
        """Connect to sync server and start persistent synchronization."""
        logger.info(f"Client {self.client_id} connecting to http://{self.host}:{self.port}/{self.room_name}/...")

        # Create the websocket provider
        try:
            doc = await self._create_ws_provider(
                self.host,
                self.port,
                self.room_name,
                self.doc,
            )

            # Update our document reference to the connected one
            self.doc = doc
            self.files_map = doc.get("files", type=Map)
            self.files_map.observe(self._on_map_change)
            self._connected = True
            self._ws_provider = True  # Just mark as connected

            logger.info(f"[{self.room_name}] Client {self.client_id} successfully connected.")
        except Exception as e:
            logger.error(f"[{self.room_name}] Failed to connect client {self.client_id}: {e}")
            self._connected = False
            await self._cleanup_provider_resources()
            self._ws_provider = None

    async def disconnect(self):
        """Disconnect from the sync server and cleanup resources."""
        import asyncio

        if self._ws_provider and self._connected:
            try:
                await self._cleanup_provider_resources()
            except asyncio.CancelledError:
                # Handle cancellation gracefully during shutdown
                logger.debug(f"[{self.room_name}] Disconnect cancelled for client {self.client_id}")
            except Exception as e:
                logger.error(f"[{self.room_name}] Error during disconnect for client {self.client_id}: {e}")
            finally:
                self._ws_provider = None
                self._connected = False
                logger.info(f"[{self.room_name}] Client {self.client_id} disconnected.")

    def _on_map_change(self, event):
        """Handle changes to the shared map."""
        logger.info(f"[{self.room_name}] Client {self.client_id} detected change: {event}")

    async def add_file_signature(
        self,
        file_name: str,
        file_hash: str,
        signature: str,
        username: str,
        user_id: str,
        signed_on: datetime,
        expiration_date: Optional[datetime] = None,
        persist: Optional[bool] = False,
    ) -> None:
        """Add a file signature to the storage.

        Args:
            file_name: Name of the file
            file_hash: Hash of the file
            signature: The file's signature
            username: Display name of the user who signed the file
            user_id: ID of the user who signed the file
            signed_on: Timestamp of when the signature was created
            expiration_date: Optional expiration date for the signature
            persist: True if the update should trigger a save of the state on file, False otherwise
        """
        # Use provided username or fall back to user_id if not provided
        display_name = username if username else user_id

        file = {
            "id": shortuuid.uuid(),
            "name": file_name,
            "hash": file_hash,
            "signature": signature,
            "user_id": user_id,
            "username": display_name,
            "signed_on": str(signed_on.isoformat()),
        }

        # Add expiration date if provided
        if expiration_date:
            file["expiration_date"] = str(expiration_date.isoformat())

        # Add the file to the files map
        with self.doc.transaction():
            self.files_map[file["id"]] = file

        if persist:
            self.save_signatures_to_file()

    async def remove_file_signature(self, file_id: str, persist: Optional[bool] = False) -> None:
        """Remove a file signature from the storage.

        Args:
            file_id: ID of the file signature to remove
            persist: True if the removal should trigger a save of the state on file,
                    False otherwise
        """
        file = self.files_map[file_id]
        if file:
            with self.doc.transaction():
                del self.files_map[file_id]

        if persist:
            self.save_signatures_to_file()

    def get_signatures(self) -> list:
        """Retrieve all file signatures stored in the document.

        Converts the CRDT data structures into standard Python dictionaries for easier
        manipulation and returns them as a list. Each dictionary contains the complete
        signature information including file name, hash, signature value, user ID,
        timestamp, and optional expiration date.
        """
        signatures = []

        for _, file in self.files_map.items():
            signatures.append(dict(file))

        return signatures

    def save_signatures_to_file(self) -> None:
        """Save the file signatures to a persistent storage file.

        Serializes the current state of the CRDT document containing all signatures
        and writes it to the default storage location (.storage/signatures.bin).
        Creates the storage directory if it doesn't exist.
        """
        # Get the CRDT document state as bytes
        doc_updates = self.doc.get_update()

        # Ensure storage directory exists
        os.makedirs(".storage", exist_ok=True)

        # Write the binary state to file
        with open(".storage/signatures.bin", "wb") as f:
            f.write(doc_updates)

        print("\nSignatures saved to file.\n")

    def load_signatures_from_file(self) -> None:
        """Load signature data from persistent storage into the current document.

        Attempts to read the serialized CRDT document from the default storage location
        (.storage/signatures.bin) and applies it to the current document instance.
        If the storage file doesn't exist, logs an error message but continues execution.

        """
        try:
            with open(".storage/signatures.bin", "rb") as f:
                doc_updates = f.read()
        except FileNotFoundError:
            logging.error("\nCould not load state from .storage/signatures.bin.\n")
            return

        # Apply the update to the current document
        self.doc.apply_update(doc_updates)
        print("\nSignatures loaded from file.\n")

    def get_signatures_table(self) -> None:
        """Get all file signatures stored in the document as a formatted table."""
        # Create table with appropriate columns
        table = Table(title="File Signatures")
        table.add_column("File Name", style="cyan")
        table.add_column("Hash", style="magenta")
        table.add_column("Signature", style="green", overflow="fold")
        table.add_column("User ID", style="blue")
        table.add_column("Signed On", style="yellow")
        table.add_column("Expiration Date", style="red")

        # Get all signatures and add them to the table
        signatures = self.get_signatures()
        for sig in signatures:
            table.add_row(
                sig["name"],
                sig["hash"],
                sig["signature"],
                sig["user_id"],
                sig["signed_on"],
                sig.get("expiration_date", "N/A"),
            )

        Console().print(table)


class UserStorage:
    """Storage for user date using pycrdt's CRDT data structures."""

    def __init__(
        self,
        client_id: str,
        host: str,
        port: int,
        room_name: str = "users",
        from_file: bool = False,
    ):
        """Initialize a new UserStorage instance.

        Args:
            client_id: Unique identifier for this client
            host: Hostname or IP address of the server
            port: Port number of the server
            room_name: Name of the room in the server for this client
            from_file: If True, attempts to load the document state from the default
                      storage file (.storage/users.bin). Defaults to False.
        """
        self.client_id = client_id
        self.host = "server" if os.environ.get("IS_CONTAINER") == "true" else host
        self.port = port
        self.room_name = room_name
        self.doc = Doc()
        self.users_map = self.doc.get("users", type=Map)
        self._connected = False
        self._ws_provider = None
        self._provider_task = None

        # Load from file if requested
        if from_file:
            self.load_users_from_file()

    async def _create_ws_provider(
        self,
        host,
        port,
        room_name,
        doc=None,
        log=None,
    ):
        """Create a websocket provider for connecting to the server."""
        doc = Doc() if doc is None else doc

        self._websocket = None
        self._provider = None
        self._connection_task = None

        try:
            # Create the websocket connection
            self._websocket_context = aconnect_ws(f"http://{host}:{port}/{room_name}")
            self._websocket = await self._websocket_context.__aenter__()

            # Create the provider
            self._provider_context = Provider(doc, HttpxWebsocket(self._websocket, room_name), log=log)
            self._provider = await self._provider_context.__aenter__()

            # Store contexts for cleanup
            self._contexts = [self._provider_context, self._websocket_context]

            return doc

        except Exception as e:
            logger.error(f"Error creating websocket provider: {e}")
            # Clean up any partially created resources
            await self._cleanup_provider_resources()
            raise

    async def _cleanup_provider_resources(self):
        """Clean up websocket provider resources safely."""
        import asyncio

        # Clean up contexts in reverse order
        if hasattr(self, '_contexts'):
            for context in reversed(self._contexts):
                try:
                    await context.__aexit__(None, None, None)
                except asyncio.CancelledError:
                    # Handle cancellation gracefully - don't propagate
                    logger.debug(f"[{self.room_name}] Context cleanup cancelled for client {self.client_id}")
                except Exception as e:
                    logger.debug(f"[{self.room_name}] Error cleaning up context for client {self.client_id}: {e}")
            self._contexts = []

        # Reset state
        self._websocket = None
        self._provider = None

    async def connect(self):
        """Connect to sync server and start persistent synchronization."""
        logger.info(f"Client {self.client_id} connecting to http://{self.host}:{self.port}/{self.room_name}/...")

        # Create the websocket provider
        try:
            doc = await self._create_ws_provider(
                self.host,
                self.port,
                self.room_name,
                self.doc,
            )

            # Update our document reference to the connected one
            self.doc = doc
            self.users_map = doc.get("users", type=Map)
            self.users_map.observe(self._on_map_change)
            self._connected = True
            self._ws_provider = True  # Just mark as connected

            logger.info(f"[{self.room_name}] Client {self.client_id} successfully connected.")
        except Exception as e:
            logger.error(f"[{self.room_name}] Failed to connect client {self.client_id}: {e}")
            self._connected = False
            await self._cleanup_provider_resources()
            self._ws_provider = None

    async def disconnect(self):
        """Disconnect from the sync server and cleanup resources."""
        import asyncio

        if self._ws_provider and self._connected:
            try:
                await self._cleanup_provider_resources()
            except asyncio.CancelledError:
                # Handle cancellation gracefully during shutdown
                logger.debug(f"[{self.room_name}] Disconnect cancelled for client {self.client_id}")
            except Exception as e:
                logger.error(f"Error during disconnect for client {self.client_id}: {e}")
            finally:
                self._ws_provider = None
                self._connected = False
                logger.info(f"[{self.room_name}] Client {self.client_id} disconnected.")

    def _on_map_change(self, event):
        """Handle changes to the shared map."""
        logger.info(f"[{self.room_name}] Client {self.client_id} detected change: {event}")

    def add_user(
        self,
        user_name: str,
        user_id: str,
        user_public_key: str,
        created_on: datetime,
        persist: Optional[bool] = False,
    ) -> None:
        """Add a user to the storage.

        Creates a new user entry with the provided information and adds it to the
        CRDT document. The user includes its name, unique ID, public key, and
        timestamp information. Optionally persists the updated state to disk.

        Args:
            user_name: Name of the user being added
            user_id: Unique identifier of the user being added
            user_public_key: Public key of the user being added
            created_on: Timestamp when the user was created
            persist: If True, immediately saves the updated state to disk.
                    Defaults to False.

        """
        user = {
            "name": user_name,
            "id": user_id,
            "public_key": user_public_key,
            "created_on": str(created_on.isoformat()),
        }

        with self.doc.transaction():
            self.users_map[user["id"]] = user

        if persist:
            self.save_users_to_file()

    def save_users_to_file(self) -> None:
        """Save the user data to a persistent storage file.

        Serializes the current state of the CRDT document containing all user
        data and writes it to the default storage location (.storage/users.bin).
        Creates the storage directory if it doesn't exist.

        """
        # Get the CRDT document state as bytes
        doc_updates = self.doc.get_update()

        # Ensure storage directory exists
        os.makedirs(".storage", exist_ok=True)

        # Write the binary state to file
        with open(".storage/users.bin", "wb") as f:
            f.write(doc_updates)

        print("\nUsers data saved to file.\n")

    def load_users_from_file(self) -> None:
        """Load user data from persistent storage into the current document.

        Attempts to read the serialized CRDT document from the default storage location
        (.storage/users.bin) and applies it to the current document instance.
        If the storage file doesn't exist, logs an error message but continues execution.

        """
        try:
            with open(".storage/users.bin", "rb") as f:
                doc_updates = f.read()
        except FileNotFoundError:
            logging.error("\nCould not load state from.storage/users.bin.\n")
            return

        # Apply the update to the current document
        self.doc.apply_update(doc_updates)
        print("\nUsers data loaded from file.\n")

    def get_users(self) -> list:
        """Retrieve all user data stored in the document.

        Converts the CRDT data structures into standard Python dictionaries for easier
        manipulation and returns them as a list. Each dictionary contains the complete
        user information including name, ID, public key, and creation timestamp.

        """
        users = []

        for _, user in self.users_map.items():
            users.append(dict(user))

        return users

    def get_user_public_key(self, user_id: str):
        """Retrieve the public key of a user by its ID.

        Args:
            user_id: ID of the user to retrieve the public key for
        """
        user = self.users_map[user_id]

        if user:
            return user["public_key"]
