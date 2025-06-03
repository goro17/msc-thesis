"""Functions to deal with storage of signatures and user keys."""

import logging
import os
import random
import string
import time
from datetime import datetime
from typing import Optional

from pycrdt import Array, Doc, Map
from rich.console import Console
from rich.table import Table


class FileSignatureStorage:
    """Storage for file signatures using pycrdt's CRDT data structures."""

    def __init__(self, from_file: bool = False):
        """Initialize a new FileSignatureStorage.

        Args:
            from_file: If True, attempts to load the document state from the default
                      storage file (.storage/signatures.bin). Defaults to False.
        """
        self.doc = Doc()

        # Create a root map for our document
        self.doc["files"] = Array([])

        # Load from file if requested
        if from_file:
            self.load_signatures_from_file()

    def _generate_unique_id(self, file_name: str, user_id: str, timestamp: datetime) -> str:
        """Generate a unique ID for a file signature.

        Creates a deterministic 16-character alphanumeric ID based on the file name,
        user ID, and timestamp. This ensures that the same file signed by different users
        or at different times will have different IDs.

        Args:
            file_name: Name of the file being signed
            user_id: Identifier of the user who signed the file
            timestamp: Timestamp when the signature was created

        Returns:
            str: A 16-character alphanumeric unique ID
        """
        # Convert timestamp to Unix timestamp (seconds since epoch)
        unix_timestamp = int(time.mktime(timestamp.timetuple()))

        # Create a seed based on the combination of inputs
        seed_str = f"{file_name}_{user_id}_{unix_timestamp}"

        # Use the seed to initialize the random generator for reproducibility
        random.seed(seed_str)

        # Generate a 16-character alphanumeric ID
        chars = string.ascii_letters + string.digits
        unique_id = "".join(random.choice(chars) for _ in range(16))

        return unique_id

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

        file_map = Map(
            {
                "id": self._generate_unique_id(file_name, user_id, signed_on),
                "name": file_name,
                "hash": file_hash,
                "signature": signature,
                "user_id": user_id,
                "username": display_name,
                "signed_on": str(signed_on.isoformat()),
            }
        )

        # Add the file map to the files array first to integrate it with the document
        self.doc["files"].append(file_map)

        # Add expiration date if provided
        if expiration_date:
            file_map["expiration_date"] = str(expiration_date.isoformat())

        if persist:
            self.save_signatures_to_file()

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
        files_array = self.doc["files"]

        for i in range(len(files_array)):
            file_map = files_array[i]
            signatures.append(dict(file_map))

        return signatures

    def find_signature(self, file_name: str, file_hash: Optional[str] = None):
        """Find a signature by file name and optionally by hash.

        Args:
            file_name: Name of the file to find
            file_hash: Optional hash of the file to find

        Returns:
            dict or None: The signature if found, None otherwise
        """
        files = self.doc["files"]

        for i in range(len(files)):
            file_map = files[i]
            if file_map["name"] == file_name:
                if file_hash is None or file_map["hash"] == file_hash:
                    return dict(file_map)

        return None

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

    def __init__(self, from_file: bool = False):
        """Initialize a new UserStorage instance.

        Creates a new CRDT document with an empty array for storing user data.
        If requested, attempts to load existing user data from the default
        storage location.

        Args:
            from_file: If True, attempts to load the document state from the default
                      storage file (.storage/users.bin). Defaults to False.
        """
        self.doc = Doc()

        # Create a root map for our document
        self.doc["users"] = Array([])

        # Load from file if requested
        if from_file:
            self.load_users_from_file()

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

        Returns:
            None
        """
        user_map = Map(
            {
                "name": user_name,
                "id": user_id,
                "public_key": user_public_key,
                "created_on": str(created_on.isoformat()),
            }
        )

        # Add the file map to the files array first to integrate it with the document
        self.doc["users"].append(user_map)

        if persist:
            self.save_users_to_file()

    def save_users_to_file(self) -> None:
        """Save the user data to a persistent storage file.

        Serializes the current state of the CRDT document containing all user
        data and writes it to the default storage location (.storage/users.bin).
        Creates the storage directory if it doesn't exist.

        Returns:
            None
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

        Returns:
            None
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

        Returns:
            list: A list of dictionaries, each containing a complete user record.
                 Returns an empty list if no users are stored.
        """
        users = []
        users_array = self.doc["users"]

        for i in range(len(users_array)):
            user_map = users_array[i]
            users.append(dict(user_map))

        return users

    def find_user(self, user_id: str):
        """Find a user by ID.

        Args:
            user_id: ID of the user to find

        Returns:
            dict or None: The user if found, None otherwise
        """
        users = self.doc["users"]

        for i in range(len(users)):
            user_map = users[i]
            if user_map["id"] == user_id:
                return dict(user_map)

        return None

