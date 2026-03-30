"""Experimental UI wrapper that provides a minimal, consistent terminal interface.

Manages the Jupyter process lifecycle (rather than replacing the process)
and displays formatted URLs, while handling graceful shutdown.
Supports Jupyter Lab, Notebook, and NBClassic variants.
"""

from __future__ import annotations

import atexit
import os
import re
import signal
import subprocess
import tempfile
import time
from pathlib import Path
from queue import Queue
from threading import Event, Thread

from uv import find_uv_bin

from ._console import console
from ._version import __version__

_SELECTING_RE = re.compile(r"^DEBUG Selecting: (.+?)==")

_PKG_CHANGE_RE = re.compile(r"^\s*[+~-]\s+(.+?)==")


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


def _cycle_names(status: object, names: list[str], stop: Event) -> None:
    """Continuously cycle through package names in the spinner status."""
    i = 0
    while not stop.wait(0.1):
        if names:
            status.update(f"[dim]{names[i % len(names)]}[/dim]")  # type: ignore[union-attr]
            i += 1


def process_output(  # noqa: C901, PLR0912, PLR0915
    filename: str,
    output_queue: Queue,
) -> None:
    status = console.status("[dim]Resolving dependencies...[/dim]", spinner="dots")
    status.start()
    start = time.time()

    packages: list[str] = []
    log_lines: list[str] = []
    pkg_count = 0
    stop_cycling = Event()
    cycling = False

    name_version: None | tuple[str, str] = None

    while name_version is None:
        line = output_queue.get()
        if line is None:
            break
        line = line.strip()
        if not line or line.startswith(("Reading inline script", "DEBUG Reading")):
            continue

        # Keep all non-debug lines for error reporting
        if not line.startswith("DEBUG"):
            log_lines.append(line)

        if line.startswith("JUV_MANGED="):
            parts = line[len("JUV_MANGED=") :].split(",")
            name_version = (parts[0], parts[1])
            if len(parts) > 2:  # noqa: PLR2004
                pkg_count = int(parts[2])
            continue

        # Collect individual package names as they're selected
        if match := _SELECTING_RE.match(line):
            name = match.group(1)
            packages.append(name)
            # Start the cycling animation once we have a few names
            if not cycling and len(packages) >= 2:  # noqa: PLR2004
                cycling = True
                stop_cycling.clear()
                Thread(
                    target=_cycle_names,
                    args=(status, packages, stop_cycling),
                    daemon=True,
                ).start()
            elif not cycling:
                status.update(f"[dim]{name}[/dim]")
            continue

        # Per-package install lines (+ name==ver) — collect and keep cycling
        if match := _PKG_CHANGE_RE.match(line):
            name = match.group(1)
            if name not in packages:
                packages.append(name)
            continue

        # Skip download progress lines
        if line.startswith(("Downloading ", "Downloaded ")):
            continue

        # Skip verbose log lines (DEBUG, WARN, etc.)
        if line.startswith(("DEBUG", "WARN")):
            continue

        # Show summary lines (Resolved, Prepared, Installed, etc.)
        # and pause the cycling animation while they're displayed
        stop_cycling.set()
        cycling = False
        status.update(f"[dim]{line}[/dim]")

    stop_cycling.set()

    if name_version is None:
        status.stop()
        from ._console import err_console

        err_console.print("[bold red]error[/bold red]: setup failed")
        for log_line in log_lines:
            err_console.print(f"  {log_line}", highlight=False)
        return

    jupyter, version = name_version

    path = {
        "jupyterlab": f"/tree/{filename}",
        "notebook": f"/notebooks/{filename}",
        "nbclassic": f"/notebooks/{filename}",
    }[jupyter]

    def display(url: str) -> None:
        end = time.time()
        elapsed_ms = (end - start) * 1000

        time_str = (
            f"[b]{elapsed_ms:.0f}[/b] ms"
            if elapsed_ms < 1000  # noqa: PLR2004
            else f"[b]{elapsed_ms / 1000:.1f}[/b] s"
        )

        env_line = ""
        if pkg_count > 0:
            env_line = (
                f"\n  [dim][green b]➜[/green b]  [b]Env:[/b]"
                f"      {pkg_count} packages[/dim]"
            )

        console.print(
            f"""
  [green][b]juv[/b] v{__version__}[/green] [dim]ready in[/dim] [white]{time_str}[/white]

  [green b]➜[/green b]  [b]Local:[/b]    {url}
  [dim][green b]➜[/green b]  [b]Jupyter:[/b]  {jupyter} v{version}[/dim]{env_line}
  """,
            highlight=False,
            no_wrap=True,
        )

    url = None
    server_started = False

    while url is None:
        line = output_queue.get()
        if line is None:
            break

        if line.startswith("[") and not server_started:
            status.update("[dim]Starting Jupyter server...[/dim]")
            server_started = True

        if "http://" in line:
            url = format_url(extract_url(line), path)

    status.stop()
    if url:
        display(url)

    # Only pass through critical Jupyter server errors
    while True:
        line = output_queue.get()
        if line is None:
            break
        if line.startswith("[C"):
            console.print(line.rstrip(), highlight=False)


def run(
    script: str,
    args: list[str],
    filename: str,
    lockfile_contents: str | None,
    dir: Path,  # noqa: A002
) -> None:
    output_queue: Queue[str | None] = Queue()

    with tempfile.NamedTemporaryFile(
        mode="w+",
        delete=False,
        suffix=".py",
        dir=dir,
        prefix="juv.tmp.",
        encoding="utf-8",
    ) as f:
        script_path = Path(f.name)
        lockfile = Path(f"{f.name}.lock")
        f.write(script)
        f.flush()
        env = os.environ.copy()

        if lockfile_contents:
            lockfile.write_text(lockfile_contents)
            env["JUV_LOCKFILE_PATH"] = str(lockfile)

        process = subprocess.Popen(  # noqa: S603
            [os.fsdecode(find_uv_bin()), "-v", *args, f.name],
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            preexec_fn=os.setsid,  # noqa: PLW1509
            text=True,
            env=env,
        )

        output_thread = Thread(
            target=process_output,
            args=(filename, output_queue),
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
            lockfile.unlink(missing_ok=True)
            output_queue.put(None)
            output_thread.join()

        # ensure the process is fully cleaned up before deleting script
        process.wait()
        # unlink after process has exited
        atexit.register(lambda: script_path.unlink(missing_ok=True))
