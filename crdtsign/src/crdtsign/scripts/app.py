"""Web server command for crdtsign."""

from pathlib import Path

import click

from crdtsign.api import create_app


@click.command()
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
@click.option(
    "--debug/--no-debug",
    default=False,
    help="Run the server in debug mode.",
)
def app(host, port, debug):
    """Run the crdtsign web application.

    This command starts a Flask web server that provides a webpage
    for managing file signatures. It allows users to view, create, verify,
    and delete file signatures through a browser.
    """
    # Ensure storage directory exists
    Path(".storage").mkdir(exist_ok=True)

    # Create and run the Flask app
    app = create_app()
    click.echo(f"\nStarting crdtsign web server at http://{host}:{port}\n")
    app.run(host=host, port=port, debug=debug)


if __name__ == "__main__":
    app()
