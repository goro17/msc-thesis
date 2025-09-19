"""User management functionality for crdtsign."""

import json
import logging
import os
import random
import string
from datetime import datetime
from pathlib import Path
from typing import Optional


class User:
    """User management for crdtsign application.

    This class handles user registration, ID generation, and persistence.
    """

    # The generated user file stored in the .storage/cache directory.
    CACHE_DIR = Path(".storage/cache")

    def __init__(self, user_id: Optional[str] = None, username: Optional[str] = None):
        """Initialize a User instance.

        This method automatically handles loading existing user data or creating new user data.
        It checks for existing user files in the cache directory and loads them if found,
        or creates a new user and saves it to file if no existing user is found.

        Args:
            user_id: Optional user ID. If not provided, will be loaded from file or generated.
            username: Optional username. Can be set during initial registration or updates.
            force_new: Internal flag to force creation of new user (used by class methods).
        """
        # Ensure storage directories exist
        os.makedirs(self.CACHE_DIR, exist_ok=True)

        # If forcing new user creation, skip loading
        # if force_new:
        #     self.user_id = user_id if user_id else self._generate_user_id()
        #     self.username = username
        #     self.registration_date = datetime.now()
        #     self._save_to_file()
        #     return

        # Try to load existing user data
        loaded_data = self._load_from_file()

        if loaded_data:
            self.user_id = loaded_data["user_id"]
            self.username = loaded_data["username"]
            self.registration_date = loaded_data["registration_date"]
        else:
            # Create new user
            self.user_id = user_id if user_id else self._generate_user_id()
            self.username = username
            self.registration_date = datetime.now()
            self._save_to_file()
            logging.info(f"Created new user with ID: {self.user_id} and username: {username}")

    def _generate_user_id(self) -> str:
        """Generate a unique user ID.

        Returns:
            str: A 12-character alphanumeric unique ID
        """
        # Generate a 12-character alphanumeric ID
        chars = string.ascii_letters + string.digits
        return "user_" + "".join(random.choice(chars) for _ in range(12))

    def _save_to_file(self) -> None:
        """Internal method to save user information to file.

        Serializes the current user information as JSON and writes it to the
        storage location in .storage/cache/user_<userid>.json.
        """
        # Prepare user data as dictionary
        user_data = {
            "user_id": self.user_id,
            "username": self.username,
            "registration_date": self.registration_date.isoformat(),
        }

        # Get the file path for this user
        file_path = self.CACHE_DIR / f"{self.user_id}.json"

        # Write user information to JSON file
        with open(file_path, "w") as f:
            json.dump(user_data, f, indent=2)

        logging.info(f"User information saved to {file_path}")

    def _load_from_file(self) -> Optional[dict]:
        """Internal method to load user information from file.

        First tries to load from the new JSON format in .storage/cache/.
        If not found, attempts to load from the legacy format (.storage/user.bin).

        Returns:
            dict: User data dictionary if user file exists, None otherwise.
        """
        # Try to find any user file in the cache directory
        if not self.CACHE_DIR.exists():
            return None

        # Look for any user JSON files in the cache directory
        user_files = list(self.CACHE_DIR.glob("user_*.json"))
        if user_files:
            # Use the first user file found
            with open(user_files[0], "r") as f:
                user_data = json.load(f)
                try:
                    registration_date = datetime.fromisoformat(user_data.get("registration_date"))
                except (ValueError, TypeError):
                    registration_date = datetime.now()

                return {
                    "user_id": user_data.get("user_id"),
                    "username": user_data.get("username"),
                    "registration_date": registration_date,
                }
        return None

    def set_username(self, username: str):
        """Register the connected user with the given username."""
        self.username = username
        self._save_to_file()
        logging.info(f"{self.user_id} successfully registered as '{self.username}'")
