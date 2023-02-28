# Copyright © PyroLab Project Contributors
# Licensed under the terms of the GNU GPLv3+ License
# (see pyrolab/__init__.py for details)

"""
Command Line Interface
======================

Usage: pyrolab [OPTIONS] COMMAND [ARGS]...

Try ``pyrolab --help`` for help.
"""
import shutil
from pathlib import Path

import typer

from pyromonitor import CONFIG_FILE
from pyromonitor.config import CONFIG


app = typer.Typer(no_args_is_help=True)


def _version_callback(value: bool=True) -> None:
    if value:
        from pyromonitor import __version__
        typer.echo(f"PyroMonitor {__version__}")
        raise typer.Exit()

@app.callback()
def main(
    version: bool = typer.Option(False, "--version", "-v", help="Show the version and exit.", callback=_version_callback, is_eager=True),
):
    return

@app.command()
def configure(
    filename: str,
):
    """
    Load a server configuration file.
    """
    filename = Path(filename)
    if not filename.exists():
        raise FileNotFoundError(f"File does not: '{filename}'")
    shutil.copy(filename, CONFIG_FILE)

@app.command()
def up(
    host: str = typer.Option(None, "--host", "-h", help="Host IP to run app on (default localhost)"),
    port: int = typer.Option(None, "--port", "-p", help="Host port to run app on (default 8080)"),
    nameserver: str = typer.Option(None, "--nameserver", "-n", help="Nameserver to use"),
    ns_port: int = typer.Option(None, "--ns_port", "-p", help="Nameserver port"),
):
    """
    Launch the monitoring web app.
    """
    if host:
        CONFIG.host = host
    if port:
        CONFIG.port = port
    if nameserver:
        CONFIG.nameserver = nameserver
    if ns_port:
        CONFIG.ns_port = ns_port
    
    from pyromonitor import create_app
    webapp = create_app()

    from waitress import serve
    uri = f'{CONFIG.host}:{CONFIG.port}'
    
    print("")
    print(f"    Serving on http://{uri}")
    print(f"    (press CTRL+C to quit)")

    serve(webapp, listen=uri, threads=4, clear_untrusted_proxy_headers=True)
