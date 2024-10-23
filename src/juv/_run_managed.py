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


from rich.console import Console


def get_version(jupyter: str):
    with_jupyter = {
        "lab": "--with=jupyterlab",
        "notebook": "--with=notebook",
        "nbclassic": "--with=nbclassic",
    }[jupyter]
    result = subprocess.run(
        [
            "uvx",
            "--quiet",
            "--from=jupyter-core",
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


def process_output(console: Console, jupyter: str, filename: str, output_queue: Queue):
    version = get_version(jupyter)
    name = f"jupyter {jupyter}".upper()

    console.clear()
    version_str = f" v{version}" if version else ""
    console.print()
    console.print(f"  [green][b]{name}[/b]{version_str}[/green]")
    console.print()

    local_url = False
    direct_url = False

    path = {
        "lab": f"/tree/{filename}",
        "notebook": f"/notebooks/{filename}",
        "nbclassic": f"/notebooks/{filename}",
    }[jupyter]

    while True:
        line = output_queue.get()
        if line is None:
            break

        if "http://" in line:
            url = extract_url(line)
            if "localhost" in url and not local_url:
                console.print(
                    f"  [green b]➜[/green b]  [b]Local:[/b]   {format_url(url, path)}"
                )
                local_url = True
            elif not direct_url:
                console.print(
                    f"  [dim][green b]➜[/green b]  [b]Direct:[/b]  {format_url(url, path)}[/dim]"
                )
                direct_url = True


def run(
    uvx_args: list[str],
    filename: str,
    jupyter: typing.Literal["lab", "notebook", "nbclassic"],
):
    console = Console()
    output_queue = Queue()
    process = subprocess.Popen(
        ["uvx"] + uvx_args,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        preexec_fn=os.setsid,
    )
    output_thread = Thread(
        target=process_output, args=(console, jupyter, filename, output_queue)
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
