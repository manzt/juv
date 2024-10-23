"""
Experimental UI wrapper for Jupyter commands that provides a minimal, consistent terminal interface.

Manages the Jupyter process lifecycle (rather than replacing the process) and displays formatted URLs,
while handling graceful shutdown. Supports Jupyter Lab, Notebook, and NBClassic variants.
"""

import re
import signal
import subprocess
from queue import Queue
from threading import Thread
import os
import typing
import time

from uv import find_uv_bin
from ._version import __version__

from rich.console import Console


def get_version(jupyter: str, version: str | None):
    with_jupyter = {
        "lab": "--with=jupyterlab",
        "notebook": "--with=notebook",
        "nbclassic": "--with=nbclassic",
    }[jupyter]
    if version:
        with_jupyter += f"=={version}"
    result = subprocess.run(
        [
            os.fsdecode(find_uv_bin()),
            "tool",
            "run",
            with_jupyter,
            "jupyter",
            jupyter,
            "--version",
        ],
        capture_output=True,
        text=True,
    )
    return result.stdout.strip()


def extract_url(log_line: str) -> str:
    match = re.search(r"http://[^\s]+", log_line)
    assert match, f"URL not found in log line: {log_line}"
    return match.group(0)


def format_url(url: str, path: str) -> str:
    if "?" in url:
        url, query = url.split("?", 1)
        return format_url(url.rstrip("/tree"), path) + f"[dim]?{query}[/dim]"
    return f"[cyan]{re.sub(r':\d+', r'[b]\g<0>[/b]', url.rstrip("/tree"))}{path}[/cyan]"


def process_output(
    console: Console,
    jupyter: str,
    jupyter_version: str | None,
    filename: str,
    output_queue: Queue,
    clear_console: bool = False,
):
    status = console.status("Running uv...", spinner="dots")
    status.start()
    start = time.time()

    version = get_version(jupyter, jupyter_version)

    path = {
        "lab": f"/tree/{filename}",
        "notebook": f"/notebooks/{filename}",
        "nbclassic": f"/notebooks/{filename}",
    }[jupyter]

    def display(local_url: str):
        end = time.time()
        elapsed_ms = (end - start) * 1000

        time_str = (
            f"[b]{elapsed_ms:.0f}[/b] ms"
            if elapsed_ms < 1000
            else f"[b]{elapsed_ms / 1000:.1f}[/b] s"
        )
        if clear_console:
            console.clear()
        console.print(
            f"""
  [green][b]juv[/b] v{__version__}[/green] [dim]ready in[/dim] [white]{time_str}[/white]

  [green b]➜[/green b]  [b]Local:[/b]    {local_url}
  [dim][green b]➜[/green b]  [b]Jupyter:[/b]  {jupyter} v{version}[/dim]
  """,
            highlight=False,
            no_wrap=True,
        )

    local_url = None
    server_started = False

    while local_url is None:
        line = output_queue.get()

        if line.startswith("[") and not server_started:
            status.update("Jupyter server started", spinner="dots")
            server_started = True

        if "http://" in line:
            url = extract_url(line)
            if "localhost" in url and not local_url:
                local_url = format_url(url, path)

    status.stop()
    display(local_url)


def run(
    args: list[str],
    filename: str,
    jupyter: typing.Literal["lab", "notebook", "nbclassic"],
    jupyter_verison: str | None,
):
    console = Console()
    output_queue = Queue()
    process = subprocess.Popen(
        [os.fsdecode(find_uv_bin())] + args,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        preexec_fn=os.setsid,
        text=True,
    )
    output_thread = Thread(
        target=process_output,
        args=(console, jupyter, jupyter_verison, filename, output_queue),
    )
    output_thread.start()

    try:
        while True and process.stdout:
            line = process.stdout.readline()
            if not line and process.poll() is not None:
                break
            output_queue.put(line)
    except KeyboardInterrupt:
        with console.status("Shutting down..."):
            os.killpg(os.getpgid(process.pid), signal.SIGTERM)
    finally:
        output_queue.put(None)
        output_thread.join()
