"""Functions to deal with storage of signatures and user keys."""

import logging
import os
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
            from_file: If True, attempt to load the document state from file.
        """
        self.doc = Doc()

        # Create a root map for our document
        self.doc["files"] = Array([])

        # Load from file if requested
        if from_file:
            self.load_signatures_from_file()

    def add_file_signature(
        self,
        file_name: str,
        file_hash: str,
        signature: str,
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
            user_id: ID of the user who signed the file
            signed_on: Timestamp of when the signature was created
            expiration_date: Optional expiration date for the signature
            persist: True if the update should trigger a save of the state on file, False otherwise
        """
        file_map = Map(
            {
                "name": file_name,
                "hash": file_hash,
                "signature": signature,
                "user_id": user_id,
                "signed_on": str(signed_on.isoformat()),
            }
        )

        # Add expiration date if provided
        if expiration_date:
            file_map["expiration_date"] = str(expiration_date.isoformat())

        # Add the file map to the files array
        self.doc["files"].append(file_map)

        if persist:
            self.save_signatures_to_file()

    def save_signatures_to_file(self) -> None:
        """Save the file signatures to a file in storage."""
        # Get the CRDT document state as bytes
        doc_updates = self.doc.get_update()

        # Ensure storage directory exists
        os.makedirs(".storage", exist_ok=True)

        # Write the binary state to file
        with open(".storage/signatures.bin", "wb") as f:
            f.write(doc_updates)

        print("\nSignatures saved to file.\n")

    def load_signatures_from_file(self) -> None:
        """Load the CRDT corresponding to the signature collection from file and update the current document."""
        try:
            with open(".storage/signatures.bin", "rb") as f:
                doc_updates = f.read()
        except FileNotFoundError:
            logging.error("\nCould not load state from .storage/signatures.bin.\n")
            return

        # Apply the update to the current document
        self.doc.apply_update(doc_updates)
        print("\nSignatures loaded from file.\n")

    def get_signatures(self):
        """Get all file signatures stored in the document.

        Returns:
            list: A list of all file signatures in the document.
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
        files_array = self.doc["files"]

        for i in range(len(files_array)):
            file_map = files_array[i]

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
