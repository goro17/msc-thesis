"""Methods related to file management."""

import hashlib
import os
from typing import List, Optional

import lz4.frame
from loguru import logger

CHUNK_SIZE = 65536  # 64KB


def serialize_file(file_path: os.PathLike, chunk_size: Optional[int] = CHUNK_SIZE) -> List[str]:
    """Serialize the file by splitting it compressed chunks."""
    serialized_file = []

    try:
        with open(file_path, "rb") as f:
            while True:
                chunk = f.read(chunk_size)
                if not chunk:
                    break

                chunk = lz4.frame.compress(chunk)
                serialized_file.append(chunk)

        logger.info("File serialization complete.")
        return serialized_file
    except FileNotFoundError:
        logger.error(f"Could not find file '{file_path}'.")
    except Exception as e:
        logger.error(f"Error occured while serializing file: {e}")

    return []


def deserialize_file(
    input_file: List[str],
    to_file: os.PathLike,
    check_hash: Optional[str] = None,
    block_size: Optional[int] = CHUNK_SIZE,
):
    """Reconstruct the original file starting from a serialized copy."""
    try:
        with open(to_file, "wb") as f:
            for chunk in input_file:
                f.write(lz4.frame.decompress(chunk))
        logger.info(f"File successfully deserialized as '{to_file}'.")

        if check_hash:
            logger.info("Starting file integrity verification...")
            hasher = hashlib.new("sha256")

            with open(to_file, "rb") as f:
                while True:
                    block = f.read(block_size)
                    if not block:
                        break
                    hasher.update(block)

            if hasher.hexdigest() == check_hash:
                logger.info("Deserialized file is VALID.")
            else:
                logger.warning("Deserialized file is NOT VALID.")

    except Exception as e:
        logger.error(f"Error occured while deserializing file: {e}")
