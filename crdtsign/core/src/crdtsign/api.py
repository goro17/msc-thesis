"""Flask API for crdtsign functionality."""

import hashlib
import os
import signal

# import tempfile
from asyncio import sleep
from datetime import datetime, timezone
from pathlib import Path

import arrow
from hypercorn import Config
from hypercorn.asyncio import serve
from loguru import logger
from quart import Quart, jsonify, render_template, request
from quart.helpers import send_from_directory
from werkzeug.utils import secure_filename

from crdtsign.sign import get_file_hash, is_verified_signature, load_keypair, load_public_key, new_keypair, sign
from crdtsign.storage import FileSignatureStorage, UserStorage
from crdtsign.user import User
from crdtsign.utils.data_retention import get_time_until_expiration

# Initialize app
app = Quart(
    __name__,
    static_folder="static",
    template_folder="templates",
)

# Ensure storage directory exists
Path(".storage").mkdir(exist_ok=True)

# Configure upload folder
UPLOAD_FOLDER = Path(".storage/uploads")
UPLOAD_FOLDER.mkdir(exist_ok=True)
app.config["UPLOAD_FOLDER"] = UPLOAD_FOLDER

# Initialize user management
user = User()

# Initialize storage
# file_storage = FileSignatureStorage(from_file=True if Path(".storage/signatures.bin").exists() else False)
file_storage = FileSignatureStorage(
    client_id=user.user_id,
    host="0.0.0.0",
    port=8765,
    from_file=True if Path(".storage/signatures.bin").exists() else False,
)
user_storage = UserStorage(
    client_id=user.user_id, host="0.0.0.0", port=8765, from_file=True if Path(".storage/users.bin").exists() else False
)


@app.route("/", methods=["GET", "POST"])
async def index():
    """Render the main page.

    On POST, this also handles setting the username for a new user.
    """
    global user

    await file_storage.data_retention_routine()

    # Handle username registration if submitted
    if request.method == "POST":
        form = await request.form
        if "username" in form:
            username = form.get("username")
        # Only allow setting username if it's not already set
        if username and not user.username:
            # Register the user with the chosen username
            user.set_username(username)

            _, public_key = new_keypair(persist=True)

            # Add the new user to storage
            user_storage.add_user(
                user.username,
                user.user_id,
                public_key.public_bytes_raw().hex(),
                user.registration_date,
                persist=True,
            )

    # Check if we need to show the username registration form
    show_username_form = user.username is None

    return await render_template(
        "index.html", user_id=user.user_id, username=user.username, show_username_form=show_username_form
    )


@app.route("/api/signatures", methods=["GET"])
async def get_signatures():
    """Get all signatures."""
    signatures = file_storage.get_signatures()
    await file_storage.handle_files_deserialization()
    return jsonify({"signatures": signatures})


@app.route("/api/signatures/<file_id>", methods=["GET"])
async def get_signature(file_id):
    """Get a specific signature by its unique ID."""
    signatures = file_storage.get_signatures()
    for sig in signatures:
        if sig["id"] == file_id:
            print(sig)
            # sig["time_to_expiration"] = get_time_until_expiration(sig["expiration_date"])
            if "flag_data_retention" in sig:
                sig["time_to_data_retention"] = get_time_until_expiration(sig["data_retention_new_exp_date"])
            return jsonify({"signature": sig})
    return jsonify({"error": "Signature not found"}), 404


@app.route("/api/signatures", methods=["POST"])
async def sign_file():
    """Sign a file and store the signature."""
    files = await request.files
    if "file" not in files:
        return jsonify({"error": "No file part"}), 400

    file = files["file"]
    if file.filename == "":
        return jsonify({"error": "No selected file"}), 400

    # Use the registered user information from the user management system
    user_id = user.user_id
    username = user.username

    # Save a duplicate of the uploaded file in (temporary) storage
    filename = secure_filename(file.filename)
    file_path = Path(app.config["UPLOAD_FOLDER"]) / user_id
    os.makedirs(file_path, exist_ok=True)
    await file.save(file_path / filename)

    # Small sleep window to ensure correct file reading
    await sleep(0.2)

    # Get or generate keypair
    private_key, public_key = load_keypair()

    # Sign the file
    signature = sign(file_path / filename, private_key)
    sig_date = datetime.now().astimezone(datetime.now().tzinfo)

    # Hash the file content
    file_hash = get_file_hash(file_path / filename)
    # Handle expiration date if provided
    form = await request.form
    expiration_date = None
    expiration_str = form.get("expiration_date")
    if expiration_str:
        try:
            # Parse the datetime-local input format (YYYY-MM-DDThh:mm)
            expiration_date = datetime.fromisoformat(expiration_str).astimezone(datetime.now().tzinfo)
        except ValueError as e:
            # If parsing fails, log the error and ignore the expiration date
            print(f"Error parsing expiration date: {e}")
            pass

    await file_storage.add_file_signature(
        file_name=filename,
        file_hash=file_hash,
        signature=signature.hex(),
        user_id=user_id,
        username=username,
        signed_on=sig_date,
        expiration_date=expiration_date,
        persist=True,
    )

    return jsonify(
        {
            "message": "File signed successfully",
            "filename": filename,
            "signature": signature.hex(),
            "public_key": public_key.public_bytes_raw().hex(),
        }
    )


@app.route("/api/download/<file_id>", methods=["GET"])
async def download_file(file_id):
    """Retrieve file with given file ID."""
    logger.info(f"Client requested download for file '{file_id}'.")
    signatures = file_storage.get_signatures()
    for sig in signatures:
        if sig["id"] == file_id:
            try:
                return await send_from_directory(Path(".storage/uploads") / sig["user_id"], file_name=sig["name"])
            except FileNotFoundError:
                logger.error(f"File '{sig['name']}' was not found.")
            except Exception as e:
                logger.error(f"Error while retrieving file: {e}")
                return jsonify({"error": str(e)}), 400

    return jsonify({"error": f"File with ID '{file_id}' does not exist."})


@app.route("/api/verify", methods=["POST"])
async def verify_signature():
    """Verify a file signature."""
    files = await request.files
    form = await request.form

    if "file" not in files:
        return jsonify({"error": "No file part"}), 400

    file = files["file"]
    signature_hex = form.get("signature")
    public_key_hex = form.get("public_key")

    if not signature_hex or not public_key_hex:
        return jsonify({"error": "Signature and public key are required"}), 400

    if file.filename == "":
        return jsonify({"error": "No selected file"}), 400

    # Save the uploaded file
    filename = secure_filename(file.filename)
    file_path = Path(app.config["UPLOAD_FOLDER"]) / filename
    await file.save(file_path)

    try:
        # Load the public key
        public_key = load_public_key(bytes.fromhex(public_key_hex))

        # Hash the file content
        with open(file_path, "rb") as f:
            file_content = f.read()

        digest = hashlib.sha256(file_content).digest()

        # Verify the signature
        is_valid = is_verified_signature(digest, bytes.fromhex(signature_hex), public_key)

        # Clean up the uploaded file
        os.unlink(file_path)

        return jsonify({"is_valid": is_valid, "message": "Signature is valid" if is_valid else "Signature is invalid"})
    except Exception as e:
        # Clean up the uploaded file if it exists
        if file_path.exists():
            os.unlink(file_path)
        return jsonify({"error": str(e)}), 400


@app.route("/api/validate/<file_id>", methods=["GET"])
async def validate_signature(file_id):
    """Validate a signature by checking both authenticity and expiration status."""
    signatures = file_storage.get_signatures()
    for sig in signatures:
        if sig["id"] == file_id:
            # Check expiration if present
            is_expired = False
            if "data_retention_new_exp_date" in sig:
                new_expiration_date = datetime.fromisoformat(sig["data_retention_new_exp_date"])
                exp_date = arrow.get(new_expiration_date.isoformat()).to("local").format("MMMM D, YYYY (HH:mm:ss)")
                expiration_message = f"Signature valid until {exp_date}"
            else:
                expiration_message = "No expiration date set"

            if "expiration_date" in sig:
                # Parse the expiration date and ensure it's timezone-aware
                expiration_date = datetime.fromisoformat(sig["expiration_date"])

                now = datetime.now()
                is_expired = now.replace(tzinfo=timezone.utc) > expiration_date.replace(tzinfo=timezone.utc)

                exp_date = arrow.get(expiration_date.isoformat()).to("local").format("MMMM D, YYYY (HH:mm:ss)")

                if is_expired:
                    expiration_message = f"Signature expired on {exp_date}"
                else:
                    if "data_retention_new_exp_date" in sig:
                        new_expiration_date = datetime.fromisoformat(sig["data_retention_new_exp_date"])
                        exp_date = (
                            arrow.get(new_expiration_date.isoformat()).to("local").format("MMMM D, YYYY (HH:mm:ss)")
                        )
                    expiration_message = f"Signature valid until {exp_date}"

            # Ensure the signature object has the proper ISO format date with timezone
            if "expiration_date" in sig:
                sig["expiration_date"] = expiration_date.isoformat()

            digest = bytes.fromhex(sig["hash"])
            signature = bytes.fromhex(sig["signature"])
            public_key_hex = user_storage.get_user_public_key(sig["user_id"])
            public_key = load_public_key(bytes.fromhex(public_key_hex))

            return jsonify(
                {
                    "is_valid": not is_expired and is_verified_signature(digest, signature, public_key),
                    "is_expired": is_expired,
                    "message": expiration_message,
                    "signature": sig,
                }
            )

    return jsonify({"error": "Signature not found"}), 404


@app.route("/api/signatures/<file_id>", methods=["DELETE"])
async def delete_signature(file_id):
    """Delete a signature by its ID."""
    signatures = file_storage.get_signatures()
    for sig in signatures:
        if sig["id"] == file_id:
            # Remove the signature from the array
            await file_storage.remove_file_signature(file_id)
            return jsonify({"message": "Signature deleted successfully"})

    return jsonify({"error": "Signature not found"}), 404


@app.route("/api/user", methods=["GET"])
async def get_user():
    """Get the current user information."""
    return jsonify(
        {"user_id": user.user_id, "username": user.username, "registration_date": user.registration_date.isoformat()}
    )


async def run_app(host: str, port: int):
    """Connect the storage to the server and run the Quart application."""
    await file_storage.connect()
    await user_storage.connect()

    await file_storage.data_retention_routine()

    # Set up graceful shutdown handler
    shutdown_event = False

    def handle_shutdown(sig, frame):
        nonlocal shutdown_event
        logger.info("Shutdown signal received, cleaning up...")
        shutdown_event = True

    # Register signal handlers for graceful shutdown
    signal.signal(signal.SIGINT, handle_shutdown)
    signal.signal(signal.SIGTERM, handle_shutdown)

    config = Config()
    config.bind = [f"{host}:{port}"]
    try:
        await serve(app, config)
    except KeyboardInterrupt:
        logger.info("Keyboard interrupt received, shutting down...")
    finally:
        # Clean up storage connections
        logger.info("Cleaning up storage connections...")
        try:
            await file_storage.disconnect()
        except Exception as e:
            logger.error(f"Error disconnecting file storage: {e}")

        try:
            await user_storage.disconnect()
        except Exception as e:
            logger.error(f"Error disconnecting user storage: {e}")

        logger.info("Shutdown complete.")
