"""Flask API for crdtsign functionality."""

import hashlib
import os
import tempfile
from datetime import datetime, timezone
from pathlib import Path

from hypercorn import Config
from hypercorn.asyncio import serve
from quart import Quart, jsonify, render_template, request
from werkzeug.utils import secure_filename

from crdtsign.sign import (
    is_verified_signature,
    load_keypair,
    load_public_key,
    new_keypair,
    sign,
)
from crdtsign.storage import FileSignatureStorage, UserStorage
from crdtsign.user import User

# Initialize app
app = Quart(
    __name__,
    static_folder="static",
    template_folder="templates",
)

# Ensure storage directory exists
Path(".storage").mkdir(exist_ok=True)

# Configure upload folder
UPLOAD_FOLDER = Path(tempfile.gettempdir()) / "crdtsign_uploads"
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
    from_file=True if Path(".storage/signatures.bin").exists() else False
)
user_storage = UserStorage(
    client_id=user.user_id,
    host="0.0.0.0",
    port=8765,
    from_file=True if Path(".storage/users.bin").exists() else False
)


@app.route("/", methods=["GET", "POST"])
async def index():
    """Render the main page.

    On POST, this also handles setting the username for a new user.
    """
    global user

    # Handle username registration if submitted
    if request.method == "POST":
        form = await request.form
        if "username" in form:
            username = form.get("username")
        # Only allow setting username if it's not already set
        if not user.username:
            # Re-initialize user with the provided username
            user = User(username=username)

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
    return jsonify({"signatures": signatures})


@app.route("/api/signatures/<file_id>", methods=["GET"])
async def get_signature(file_id):
    """Get a specific signature by its unique ID."""
    signatures = file_storage.get_signatures()
    for sig in signatures:
        if sig["id"] == file_id:
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
    # Save the uploaded file
    filename = secure_filename(file.filename)
    file_path = Path(app.config["UPLOAD_FOLDER"]) / filename
    await file.save(file_path)

    # Get or generate keypair
    private_key, public_key = load_keypair()

    # Sign the file
    signature = sign(file_path, private_key)
    sig_date = datetime.now()

    # Hash the file content
    with open(file_path, "rb") as f:
        file_content = f.read()
    digest = hashlib.sha256(file_content).digest()

    # Use the registered user information from the user management system
    # This ensures the user info is consistent across sessions
    user_id = user.user_id
    username = user.username
    # Handle expiration date if provided
    form = await request.form
    expiration_date = None
    expiration_str = form.get("expiration_date")
    if expiration_str:
        try:
            # Parse the datetime-local input format (YYYY-MM-DDThh:mm)
            expiration_date = datetime.fromisoformat(expiration_str.replace("Z", "+00:00"))
        except ValueError as e:
            # If parsing fails, log the error and ignore the expiration date
            print(f"Error parsing expiration date: {e}")
            pass

    await file_storage.add_file_signature(
        file_name=filename,
        file_hash=digest.hex(),
        signature=signature.hex(),
        user_id=user_id,
        username=username,
        signed_on=sig_date,
        expiration_date=expiration_date,
        persist=True,
    )

    # Clean up the uploaded file
    os.unlink(file_path)

    return jsonify(
        {
            "message": "File signed successfully",
            "filename": filename,
            "signature": signature.hex(),
            "public_key": public_key.public_bytes_raw().hex(),
        }
    )


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
            expiration_message = "No expiration date set"

            if "expiration_date" in sig:
                # Parse the expiration date and ensure it's timezone-aware
                expiration_date = datetime.fromisoformat(sig["expiration_date"])
                if expiration_date.tzinfo is None:
                    # If the date is naive, assume it's in UTC
                    expiration_date = expiration_date.replace(tzinfo=timezone.utc)

                # Get current time in UTC
                now = datetime.now(timezone.utc)

                is_expired = now > expiration_date

                if is_expired:
                    expiration_message = f"Signature expired on {expiration_date.isoformat()}"
                else:
                    expiration_message = f"Signature valid until {expiration_date.isoformat()}"

            # Ensure the signature object has the proper ISO format date with timezone
            if "expiration_date" in sig:
                sig["expiration_date"] = expiration_date.isoformat()

            digest = bytes.fromhex(sig["hash"])
            signature = bytes.fromhex(sig["signature"])
            public_key_hex = user_storage.get_user_public_key(sig["user_id"])
            public_key = load_public_key(bytes.fromhex(public_key_hex))

            return jsonify({
                "is_valid": not is_expired and is_verified_signature(digest, signature, public_key),
                "is_expired": is_expired,
                "message": expiration_message,
                "signature": sig
            })

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

    config = Config()
    config.bind = [f"{host}:{port}"]
    await serve(app, config)
