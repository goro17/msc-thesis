"""Clients for connecting the CRDT storages through the sync server."""

import logging
import os
from datetime import datetime
from typing import Optional

import shortuuid
from pycrdt import Doc, Map

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class FileSignatureStorageClient:
    """Storage for file signatures using pycrdt's CRDT data structures."""

    def __init__(
        self,
        client_id: str,
        host: str,
        port: int,
        room_name: str = "file-signatures",
        from_file: bool = False,
    ):
        """Initialize a new FileSignatureStorageClient.

        Args:
            client_id: Unique identifier for this client
            host: Hostname or IP address of the server
            port: Port number of the server
            room_name: Name of the room in the server for this client
            from_file: If True, attempts to load the document state from the default
                      storage file (.storage/signatures.bin). Defaults to False.
        """
        self.client_id = client_id
        self.host = host
        self.port = port
        self.room_name = room_name
        self.doc = Doc()
        self.files_map = self.doc.get("files", type=Map)

        # Load state from file if requested
        if from_file:
            self.load_signatures_from_file()

        self.files_map.observe(self._on_map_change)

    def _on_map_change(self, event):
        """Handle changes to the shared map."""
        logger.info(f"Client {self.client_id} detected change: {event}")
        # self.save_signatures_to_file()

    def add_file_signature(
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

        # Add the file map to the files array first to integrate it with the document
        with self.doc.transaction():
            self.files_map[file["id"]] = file

        if persist:
            self.save_signatures_to_file()

    def remove_file_signature(self, file_id: str, persist: Optional[bool] = False) -> None:
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

        Returns:
            list: A list of dictionaries, each containing a complete file signature record.
                 Returns an empty list if no signatures are stored.
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

        Returns:
            None
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

        Returns:
            None
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
