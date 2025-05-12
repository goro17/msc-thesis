"""Unit tests for sign.py."""

import os
import tempfile
from pathlib import Path

import pytest
from cryptography.hazmat.primitives.asymmetric.ed448 import (
    Ed448PrivateKey,
    Ed448PublicKey,
)

from crdtsign.sign import (
    is_verified_signature,
    load_keypair,
    load_public_key,
    new_keypair,
    sign,
)


@pytest.fixture
def temp_file():
    """Create a temporary file for testing."""
    with tempfile.NamedTemporaryFile(delete=False) as tmp:
        tmp.write(b"Test content for signing")
        tmp_path = tmp.name
    yield Path(tmp_path)
    os.unlink(tmp_path)


@pytest.fixture
def temp_storage_dir():
    """Create a temporary directory for key storage."""
    original_dir = os.getcwd()
    with tempfile.TemporaryDirectory() as tmpdirname:
        os.chdir(tmpdirname)
        # Create .storage directory
        storage_dir = Path(".storage")
        storage_dir.mkdir(exist_ok=True)
        yield storage_dir
        os.chdir(original_dir)


class TestKeypairGeneration:
    """Tests for keypair generation and loading."""

    def test_new_keypair_generation(self):
        """Test that new keypairs are generated correctly."""
        private_key, public_key = new_keypair(persist=False)

        assert isinstance(private_key, Ed448PrivateKey)
        assert isinstance(public_key, Ed448PublicKey)
        assert public_key == private_key.public_key()

    def test_new_keypair_persistence(self):
        """Test that keypairs are persisted correctly."""
        private_key, public_key = new_keypair(persist=True)

        # Check that files were created
        assert Path(".storage/id_key").exists()
        assert Path(".storage/id_key.pub").exists()

        # Check file contents
        with open(".storage/id_key", "rb") as f:
            stored_private = f.read().decode("utf-8")
        with open(".storage/id_key.pub", "rb") as f:
            stored_public = f.read().decode("utf-8")

        assert stored_private == private_key.private_bytes_raw().hex()
        assert stored_public == public_key.public_bytes_raw().hex()

    def test_load_keypair(self):
        """Test loading keypair from storage."""
        # First generate and persist a keypair
        original_private, original_public = new_keypair(persist=True)

        # Then load it
        loaded_private, loaded_public = load_keypair()

        # Compare the loaded keys with the original ones
        assert (
            loaded_private.private_bytes_raw() == original_private.private_bytes_raw()
        )
        assert loaded_public.public_bytes_raw() == original_public.public_bytes_raw()

    def test_load_public_key(self):
        """Test loading a public key from bytes."""
        _, original_public = new_keypair(persist=False)
        public_bytes = original_public.public_bytes_raw()

        loaded_public = load_public_key(public_bytes)

        assert loaded_public.public_bytes_raw() == public_bytes


class TestSigningAndVerification:
    """Tests for file signing and signature verification."""

    def test_sign_file(self, temp_file):
        """Test signing a file."""
        private_key, _ = new_keypair(persist=False)
        signature = sign(temp_file, private_key)

        assert isinstance(signature, bytes)
        assert len(signature) > 0

    def test_verify_valid_signature(self, temp_file):
        """Test verifying a valid signature."""
        private_key, public_key = new_keypair(persist=False)
        signature = sign(temp_file, private_key)

        result = is_verified_signature(temp_file, signature, public_key)
        assert result is True

    def test_verify_invalid_signature(self, temp_file):
        """Test verifying an invalid signature."""
        # Generate two different keypairs
        private_key1, _ = new_keypair(persist=False)
        _, public_key2 = new_keypair(persist=False)

        # Sign with first private key
        signature = sign(temp_file, private_key1)

        # Verify with second public key (should fail)
        result = is_verified_signature(temp_file, signature, public_key2)
        assert result is False

    def test_verify_tampered_file(self, temp_file):
        """Test verifying a signature after the file has been modified."""
        private_key, public_key = new_keypair(persist=False)
        signature = sign(temp_file, private_key)

        # Modify the file after signing
        with open(temp_file, "wb") as f:
            f.write(b"Modified content")

        # Verification should fail
        result = is_verified_signature(temp_file, signature, public_key)
        assert result is False
