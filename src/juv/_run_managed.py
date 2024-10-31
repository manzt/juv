"""Experimental UI wrapper that provides a minimal, consistent terminal interface.

Manages the Jupyter process lifecycle (rather than replacing the process)
and displays formatted URLs, while handling graceful shutdown.
Supports Jupyter Lab, Notebook, and NBClassic variants.
"""

from __future__ import annotations

import os
import re
import signal
import subprocess
import time
from queue import Queue
from threading import Thread

from rich.console import Console
from uv import find_uv_bin

from ._version import __version__


def extract_url(log_line: str) -> str:
    match = re.search(r"http://[^\s]+", log_line)
    return "" if not match else match.group(0)


def format_url(url: str, path: str) -> str:
    if "?" in url:
        url, query = url.split("?", 1)
        url = url.removesuffix("/tree")
        return format_url(url, path) + f"[dim]?{query}[/dim]"
    url = url.removesuffix("/tree")
    return f"[cyan]{re.sub(r':\d+', r'[b]\g<0>[/b]', url)}{path}[/cyan]"


def process_output(
    console: Console,
    filename: str,
    output_queue: Queue,
) -> None:
    status = console.status("Running uv...", spinner="dots")
    status.start()
    start = time.time()

    name_version: None | tuple[str, str] = None

    while name_version is None:
        line = output_queue.get()

        if line.startswith("JUV_MANGED="):
            name_version = line[len("JUV_MANGED=") :].split(",")
        else:
            print(line, end="")

    jupyter, version = name_version

    path = {
        "lab": f"/tree/{filename}",
        "notebook": f"/notebooks/{filename}",
        "nbclassic": f"/notebooks/{filename}",
    }[jupyter]

    def display(local_url: str) -> None:
        end = time.time()
        elapsed_ms = (end - start) * 1000

        time_str = (
            f"[b]{elapsed_ms:.0f}[/b] ms"
            if elapsed_ms < 1000  # noqa: PLR2004
            else f"[b]{elapsed_ms / 1000:.1f}[/b] s"
        )

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
            local_url = format_url(url, path)

    status.stop()
    display(local_url)


def run(
    script: str,
    args: list[str],
    filename: str,
) -> None:
    console = Console()
    output_queue = Queue()
    process = subprocess.Popen(  # noqa: S603
        [os.fsdecode(find_uv_bin()), *args],
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        preexec_fn=os.setsid,  # noqa: PLW1509
        text=True,
        env=os.environ,
    )
    assert process.stdin is not None  # noqa: S101
    process.stdin.write(script)
    process.stdin.flush()
    process.stdin.close()

    output_thread = Thread(
        target=process_output,
        args=(console, filename, output_queue),
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
