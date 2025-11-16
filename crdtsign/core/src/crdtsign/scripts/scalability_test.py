"""Entry point for the scalability tests."""

import asyncio
import shutil
import time
from datetime import datetime
from pathlib import Path

from loguru import logger

from crdtsign.sign import get_file_hash, new_keypair, sign
from crdtsign.storage import FileSignatureStorage, UserStorage
from crdtsign.user import User

logger = logger.opt(colors=True)

UPLOAD_FOLDER = Path(".storage/uploads")
UPLOAD_FOLDER.mkdir(parents=True, exist_ok=True)


async def scale_write():
    """Run the scalability test procedure | WRITER node."""
    logger.info("Initializing user...")
    user = User()
    logger.info(f"User <cyan>{user.user_id.split('_')[-1]}</cyan> successfully initialized.")
    user.set_username("writer")

    # Initialize storage
    logger.info("Initializing CRDT storage...")
    file_storage = FileSignatureStorage(
        client_id=user.user_id,
        host="0.0.0.0",
        port=8765,
        from_file=True if Path(".storage/signatures.bin").exists() else False,
    )
    user_storage = UserStorage(
        client_id=user.user_id,
        host="0.0.0.0",
        port=8765,
        from_file=True if Path(".storage/users.bin").exists() else False,
    )
    logger.info("CRDT storage successfully initialized.")

    test_file_path = "./tests/testfile.pdf"

    await file_storage.connect()
    await user_storage.connect()
    logger.info("Connected to Sync Server.")

    private_key, public_key = new_keypair(persist=True)

    user_storage.add_user(
        user.username,
        user.user_id,
        public_key.public_bytes_raw().hex(),
        user.registration_date,
        persist=True,
    )

    logger.debug("Starting test in 3,")
    time.sleep(1.0)
    logger.debug("2,")
    time.sleep(1.0)
    logger.debug("1,")
    time.sleep(1.0)
    logger.debug("GO!")

    await file_storage.add_file_signature(
        file_name=test_file_path.split("/")[-1],
        file_hash=get_file_hash(Path(test_file_path)),
        signature=sign(Path(test_file_path), private_key).hex(),
        username=user.username,
        user_id=user.user_id,
        signed_on=datetime.now().astimezone(datetime.now().tzinfo),
        persist=True,
        serialized_file_path=Path(test_file_path),
    )

    logger.debug("Write process was completed!")

    await file_storage.disconnect()
    await user_storage.disconnect()

    logger.info("Cleaning up resources...")
    shutil.rmtree(Path(".storage"))
    logger.debug("Exiting...")


def run_scale_write():
    """Asynchronously run the scaling write routine."""
    asyncio.run(scale_write())


def scale_read():
    """Run the scalability test procedure | READER node."""
    logger.info("Initializing user...")
    user = User()
    logger.info(f"User <cyan>{user.user_id.split('_')[-1]}</cyan> successfully initialized.")
    user.set_username("writer")
    pass
