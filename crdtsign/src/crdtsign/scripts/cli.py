"""Main entry point for the CLI."""

from pathlib import Path

import click

from crdtsign.sign import is_verified_signature, load_keypair, load_public_key, new_keypair, sign


@click.command()
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
def cli(file: Path, verify: bool):
    """Sign or verify a file using Ed25519 cryptographic signatures.

    This application allows users to either 1) sign a file using an Ed25519
    private key (default behavior), or 2) verify a file's signature using the
    signer's public key (via the --verify flag)

    If no existing keypair is found when signing ('storage' folder), a new one
    will be generated.
    """
    if not verify:
        # Check whether the file was already signed
        # If not, sign it and store it in the signed folder

        # If user credentials are not stored, generate a new Ed25519 keypair
        # Otherwise, use the stored credentials.

        # Check if key files exist
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
            private_key, public_key = load_keypair()
            click.echo("\nKeypair was successfully loaded.")
            click.echo(f"Private key: {private_key.private_bytes_raw().hex()}")
            click.echo(f"Public key: {public_key.public_bytes_raw().hex()}")

        # Sign the file with the private key
        signature = sign(file, private_key)
        click.echo(click.style("\nFile was successfully signed.", fg="green"))
        click.echo(f"Signature: {signature.hex()}")
    else:
        # Alternatively, verify the signature of the file
        # Pass the public key of the signer as an argument
        signature = click.prompt("Signature", type=str)
        public_string = click.prompt("Public key", type=str)

        # Load the public key
        public_key = load_public_key(bytes.fromhex(public_string))

        # Verify the signature
        if is_verified_signature(file, bytes.fromhex(signature), public_key):
            valid_word = click.style("valid", fg="green", bold=True)
            click.echo("The provided signature is " + valid_word + ".")
        else:
            invalid_word = click.style("invalid", fg="red", bold=True)
            click.echo("The provided signature is " + invalid_word + ".")

    return


if __name__ == "__main__":
    cli()
