"""Main entry point for the CLI."""

import hashlib
from datetime import datetime
from pathlib import Path

import anyio
import click
from hypercorn import Config
from hypercorn.asyncio import serve
from pycrdt.websocket import ASGIServer, WebsocketServer

from crdtsign.api import run_app
from crdtsign.sign import (
    is_verified_signature,
    load_keypair,
    load_public_key,
    new_keypair,
    sign,
)
from crdtsign.storage import FileSignatureStorage
from crdtsign.user import User


@click.group()
def cli():
    """CRDTSign - Secure File Signature Management.

    This tool allows you to sign files, verify signatures, and manage your signature storage.
    """
    pass

# CLI SIGN / VERIFY COMMANDS
@cli.command("sign")
@click.option(
    "-f",
    "--file",
    type=click.Path(
        exists=True,
        file_okay=True,
        dir_okay=False,
        readable=True,
        resolve_path=True,
        path_type=Path,
    ),
    help="Path to the file to sign/verify.",
    required=True,
)
@click.option("-v", "--verify", is_flag=True, default=False, help="Verify a file.")
@click.option("-t", "--table", is_flag=True, default=False, help="List the signed files present in storage.")
def sign_command(file: Path, verify: bool, table: bool):
    """Sign or verify a file using Ed448 cryptographic signatures.

    This command allows users to either 1) sign a file using an Ed448
    private key (default behavior), or 2) verify a file's signature using the
    signer's public key (via the --verify flag)

    If no existing keypair is found when signing ('.storage' folder), a new one
    will be generated.
    """
    if table:
        sign_storage = FileSignatureStorage(from_file=True)
        sign_storage.get_signatures_table()
        return
    sign_storage = FileSignatureStorage(from_file=True if Path(".storage/signatures.bin").exists() else False)
    if not verify:
        # Check if a keypair has been already stored
        if not Path(".storage/id_key").exists():
            if Path(".storage").exists():
                for file in Path(".storage").iterdir():
                    file.unlink()
                Path(".storage").rmdir()
            private_key, public_key = new_keypair(persist=True)
            click.echo("\nKeypair was successfully Generated.")
            click.echo(f"Private key: {private_key.private_bytes_raw().hex()}")
            click.echo(f"Public key: {public_key.public_bytes_raw().hex()}")
        else:
            # Use the stored keypair instead of generating a new one
            private_key, public_key = load_keypair()
            click.echo("\nKeypair was successfully loaded.")
            click.echo(f"Private key: {private_key.private_bytes_raw().hex()}")
            click.echo(f"Public key: {public_key.public_bytes_raw().hex()}")

        # Sign the file with the private key
        signature = sign(file, private_key)
        sig_date = datetime.now()
        click.echo(click.style("\nFile was successfully signed.", fg="green"))
        click.echo(f"Signature: {signature.hex()}")

        with open(file, "rb") as f:
            file_content = f.read()

        # Hash the file content
        digest = hashlib.sha256(file_content).digest()

        user = User()

        # Add the signed file metadata to the file signature storage
        sign_storage.add_file_signature(
            file_name=file.name,
            file_hash=digest.hex(),
            signature=signature.hex(),
            user_id=user.user_id,
            username=user.username,  # Include username in the signature
            signed_on=datetime.strptime(str(sig_date), "%Y-%m-%d %H:%M:%S.%f"),
            expiration_date=None,
            persist=True,
        )

    else:
        signature = click.prompt("Signature", type=str)
        public_string = click.prompt("Public key", type=str)
        public_key = load_public_key(bytes.fromhex(public_string))

        # Hash the file content
        with open(file, "rb") as f:
            file_content = f.read()

        digest = hashlib.sha256(file_content).digest()

        # Verify the file's signature using the public key
        if is_verified_signature(digest, bytes.fromhex(signature), public_key):
            valid_word = click.style("valid", fg="green", bold=True)
            click.echo("\nThe provided signature is " + valid_word + ".")
        else:
            invalid_word = click.style("invalid", fg="red", bold=True)
            click.echo("\nThe provided signature is " + invalid_word + ".")

    return

# SERVER COMMAND
async def _run_server(host: str, port: int) -> None:
    """Run the sync server."""
    websocket_server = WebsocketServer()
    app = ASGIServer(websocket_server)
    config = Config()
    config.bind = [f"{host}:{port}"]
    async with websocket_server:
        await serve(app, config, mode="asgi")

@cli.command("server")
@click.option(
    "-h",
    "--host",
    default="0.0.0.0",
    help="Host to bind the server to.",
)
@click.option(
    "-p",
    "--port",
    default=8765,
    help="Port to bind the server to.",
)
def server_command(host: str, port: int) -> None:
    """Run the sync server."""
    click.echo("Starting CRDT Sync Server...")
    anyio.run(_run_server, host, port)


# WEB APP COMMAND
@cli.command("app")
@click.option(
    "--host",
    default="127.0.0.1",
    help="The host to bind the server to.",
)
@click.option(
    "--port",
    default=5000,
    type=int,
    help="The port to bind the server to.",
)
def app_command(host, port):
    """Run the crdtsign web application.

    This command starts a Flask web server that provides a webpage
    for managing file signatures. It allows users to view, create, verify,
    and delete file signatures through a browser.
    """
    # Ensure storage directory exists
    Path(".storage").mkdir(exist_ok=True)

    click.echo(f"\nStarting crdtsign web server at http://{host}:{port}\n")
    anyio.run(run_app, host, port)

if __name__ == "__main__":
    cli()
