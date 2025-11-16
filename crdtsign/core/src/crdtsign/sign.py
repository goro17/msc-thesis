"""Methods for signing and verifying files."""

import hashlib
import os
from pathlib import Path

from cryptography.exceptions import InvalidSignature
from cryptography.hazmat.primitives.asymmetric.ed448 import (
    Ed448PrivateKey,
    Ed448PublicKey,
)


def get_file_hash(file_path: os.PathLike) -> str:
    """Returns the file's hash in SHA256."""
    with open(file_path, "rb") as f:
        file_content = f.read()
    return hashlib.sha256(file_content).digest().hex()


def sign(file_path: Path, private_key: Ed448PrivateKey) -> bytes:
    """Sign a file with a private key.

    Args:
        file_path: Path to the file to be signed
        private_key: Ed448 private key used for signing

    Returns:
        bytes: The cryptographic signature of the file

    Note:
        The function hashes the file content using SHA-256 before signing
    """
    with open(file_path, "rb") as f:
        file = f.read()

    # Hash the file content
    digest = hashlib.sha256(file).digest()

    # Sign the hashed content
    signature = private_key.sign(digest)

    return signature


def is_verified_signature(file_hash: bytes, signature: bytes, public_key: Ed448PublicKey) -> bool:
    """Verify the signature of a file with the signer's public key and the file's SHA-256 hash.

    Args:
        file_hash: Hash of the file to verify
        signature: The cryptographic signature to verify
        public_key: Ed448 public key of the signer

    Returns:
        bool: True if the signature is valid, False otherwise

    Note:
        The function hashes the file content using SHA-256 before verification
    """
    try:
        public_key.verify(signature, file_hash)
        return True
    except InvalidSignature:
        return False


def new_keypair(persist: bool = False) -> (Ed448PrivateKey, Ed448PublicKey):
    """Generate a new keypair.

    Args:
        persist: If True, saves the generated keypair to disk in the .storage directory

    Returns:
        tuple[Ed448PrivateKey, Ed448PublicKey]: A tuple containing the generated private and public keys

    Note:
        When persist=True, the private and public keys are saved as hex-encoded strings
        in .storage/id_key and .storage/id_key.pub respectively
    """
    # Check if storage directory exists, create if not
    if not Path(".storage").exists():
        Path(".storage").mkdir()

    private_key = Ed448PrivateKey.generate()
    public_key = private_key.public_key()

    if persist:
        # Store the keypair in the storage directory
        with open(".storage/id_key", "wb") as file:
            file.write(bytes(private_key.private_bytes_raw().hex(), "utf-8"))
        with open(".storage/id_key.pub", "wb") as file:
            file.write(bytes(public_key.public_bytes_raw().hex(), "utf-8"))

    return private_key, public_key


def load_keypair() -> (Ed448PrivateKey, Ed448PublicKey):
    """Load the keypair from storage.

    Returns:
        tuple[Ed448PrivateKey, Ed448PublicKey]: A tuple containing the loaded private and public keys

    Raises:
        FileNotFoundError: If the key files do not exist in .storage directory
        ValueError: If the stored key data is invalid or corrupted
    """
    # Load the keypair from the storage directory
    with open(".storage/id_key", "rb") as file:
        private_bytes = bytes.fromhex(file.read().decode("utf-8"))
        private_key = Ed448PrivateKey.from_private_bytes(private_bytes)
    with open(".storage/id_key.pub", "rb") as file:
        public_bytes = bytes.fromhex(file.read().decode("utf-8"))
        public_key = Ed448PublicKey.from_public_bytes(public_bytes)

    return private_key, public_key


def load_public_key(public_bytes: bytes) -> Ed448PublicKey:
    """Load a public key from its raw bytes representation.

    Args:
        public_bytes: Raw bytes of the public key

    Returns:
        Ed448PublicKey: The public key instance

    Raises:
        ValueError: If the provided bytes are not a valid Ed448 public key
    """
    public_key = Ed448PublicKey.from_public_bytes(public_bytes)
    return public_key
