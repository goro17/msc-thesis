"""Entry point for the scalability tests."""

import asyncio
import json
import time
from datetime import datetime
from pathlib import Path

import websockets
from loguru import logger

from crdtsign.sign import get_file_hash, is_verified_signature, load_public_key, new_keypair, sign
from crdtsign.storage import FileSignatureStorage, UserStorage
from crdtsign.user import User

logger = logger.opt(colors=True)


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

    metrics = {
        "node_type": user.username,
    }

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

    logger.debug("Waiting 5 seconds before writing file...")
    time.sleep(5.0)
    metrics["write_start_time"] = str(datetime.now())
    logger.debug("Starting NOW")

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

    # Allow time for CRDT changes to propagate to the sync server
    logger.debug("Waiting for sync propagation...")
    await asyncio.sleep(0.05)

    logger.success("Write process was completed!")

    signatures = file_storage.get_signatures()
    written_file = signatures[0]

    logger.debug("Waiting 5 seconds before removing file...")
    time.sleep(5.0)
    metrics["remove_start_time"] = str(datetime.now())
    logger.debug("Starting NOW")

    await file_storage.remove_file_signature(file_id=written_file["id"], persist=True)

    # Allow time for CRDT changes to propagate to the sync server
    logger.debug("Waiting for sync propagation...")
    await asyncio.sleep(0.05)

    logger.success("Removal process was completed!")

    await file_storage.disconnect()
    await user_storage.disconnect()

    artifacts_path = Path("./tests/artifacts")
    artifacts_path.mkdir(exist_ok=True)
    with open(artifacts_path / f"{user.user_id}.json", "w") as f:
        json.dump(metrics, f)

    logger.info("Cleaning up resources...")
    # shutil.rmtree(Path(".storage"))
    logger.debug("Exiting...")


def run_scale_write():
    """Asynchronously run the scaling write routine."""
    asyncio.run(scale_write())


async def scale_read():
    """Run the scalability test procedure | READER node."""
    logger.info("Initializing user...")
    user = User()
    logger.info(f"User <cyan>{user.user_id.split('_')[-1]}</cyan> successfully initialized.")
    user.set_username("reader")

    # Initialize storage - same as writer, but READ ONLY
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

    await file_storage.connect()
    await user_storage.connect()
    logger.info("Connected to Sync Server.")

    metrics = {
        "node_type": user.username,
    }

    async def receive_update():
        uri = "ws://server:8765/file-signatures"
        websocket = None
        try:
            # Increase max_size to 10MB to handle large CRDT updates
            websocket = await websockets.connect(uri, max_size=1024 * 1024 * 10)
            logger.info(f"Connected to websocket at {uri}")

            async def websocket_listener(ws):
                try:
                    while True:
                        message = await ws.recv()
                        logger.info(f"Received update: {message}")
                        # file_storage.process_update()
                except websockets.exceptions.ConnectionClosedError as e:
                    logger.error(f"Websocket connection closed unexpectedly: {e}")
                except Exception as e:
                    logger.error(f"An error occurred: {e}")

            ws_task = asyncio.create_task(websocket_listener(websocket))

            signature_data = None
            while not signature_data:
                await asyncio.sleep(0.01)
                file_storage.load_signatures_from_file()
                signature_data = file_storage.get_signatures()
            metrics["write_time"] = str(datetime.now())

            test_file = signature_data[0]

            digest = bytes.fromhex(test_file["hash"])
            signature = bytes.fromhex(test_file["signature"])
            public_key_hex = user_storage.get_user_public_key(test_file["user_id"])
            public_key = load_public_key(bytes.fromhex(public_key_hex))

            is_valid = is_verified_signature(digest, signature, public_key)

            if is_valid:
                logger.success("Test file is VALID.")
                metrics["validation_outcome"] = "valid"
            else:
                logger.error("Test file is NOT VALID.")
                metrics["validation_outcome"] = "invalid"

            # Now wait for the file to be removed
            while len(signature_data) > 0:
                await asyncio.sleep(0.01)
                file_storage.load_signatures_from_file()
                signature_data = file_storage.get_signatures()

            metrics["remove_time"] = str(datetime.now())
            logger.success("File successfully removed.")

            # Close the websocket gracefully
            ws_task.cancel()
            await websocket.close()

        except websockets.exceptions.ConnectionClosedError as e:
            logger.error(f"Websocket connection closed unexpectedly: {e}")
        except ConnectionRefusedError as e:
            logger.error(f"Failed to connect to websocket: {e}")
        except Exception as e:
            logger.error(f"An error occurred: {e}")
        finally:
            # Ensure websocket is closed if it's still open
            if websocket:
                await websocket.close()

    await receive_update()

    await file_storage.disconnect()
    await user_storage.disconnect()

    artifacts_path = Path("./tests/artifacts")
    artifacts_path.mkdir(exist_ok=True)
    with open(artifacts_path / f"{user.user_id}.json", "w") as f:
        json.dump(metrics, f)

    logger.info("Cleaning up resources...")
    # shutil.rmtree(Path(".storage"))
    logger.debug("Exiting...")


def run_scale_read():
    """Asynchronously run the scaling write routine."""
    asyncio.run(scale_read())
