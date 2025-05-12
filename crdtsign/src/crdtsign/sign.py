"""Methods for signing and verifying files."""

import hashlib
from pathlib import Path

from cryptography.exceptions import InvalidSignature
from cryptography.hazmat.primitives.asymmetric.ed448 import (
    Ed448PrivateKey,
    Ed448PublicKey,
)


def sign(file_path: Path, private_key: Ed448PrivateKey) -> bytes:
    """Sign a file with a private key."""
    with open(file_path, "rb") as f:
        file = f.read()

    # Hash the file content
    digest = hashlib.sha256(file).digest()

    # Sign the hashed content
    signature = private_key.sign(digest)

    # TODO: Persist the hash+signature pair in the CRDT keystore

    return signature


def is_verified_signature(
    file_path: Path, signature: bytes, public_key: Ed448PublicKey
) -> bool:
    """Verify the signature of a file with the signer's public key."""
    with open(file_path, "rb") as f:
        file = f.read()

    # Hash the file content
    digest = hashlib.sha256(file).digest()

    # Verify the signature
    try:
        public_key.verify(signature, digest)
        return True
    except InvalidSignature:
        return False


def new_keypair(persist: bool = False) -> (Ed448PrivateKey, Ed448PublicKey):
    """Generate a new keypair."""
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
    """Load the keypair from storage."""
    # Load the keypair from the storage directory
    with open(".storage/id_key", "rb") as file:
        private_bytes = bytes.fromhex(file.read().decode("utf-8"))
        private_key = Ed448PrivateKey.from_private_bytes(private_bytes)
    with open(".storage/id_key.pub", "rb") as file:
        public_bytes = bytes.fromhex(file.read().decode("utf-8"))
        public_key = Ed448PublicKey.from_public_bytes(public_bytes)

    return private_key, public_key


def load_public_key(public_bytes: bytes) -> Ed448PublicKey:
    """Return the instance of Ed448OPublicKey corresponding to the public key string."""
    public_key = Ed448PublicKey.from_public_bytes(public_bytes)
    return public_key
