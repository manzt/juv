from __future__ import annotations

import pathlib
import subprocess
import time
import typing
import urllib.error
import urllib.request

import pytest

pytest.importorskip("playwright")

from playwright.sync_api import Page, expect

SELF_DIR = pathlib.Path(__file__).parent
ROOT = SELF_DIR / ".."


def juv(args: list[str], *, wait_and_check: bool = True) -> subprocess.Popen:
    process = subprocess.Popen(["uv", "run", "juv", *args], cwd=ROOT)  # noqa: S603, S607
    if wait_and_check:
        exit_code = process.wait(2)
        if exit_code != 0:
            msg = f"juv command failed: {args}, exit code: {exit_code}"
            raise RuntimeError(msg)
    return process


@pytest.fixture(autouse=True)
def notebook() -> typing.Generator[pathlib.Path]:
    path = ROOT / "smoke.ipynb"
    yield path
    path.unlink(missing_ok=True)


def test_juv_run(page: Page, notebook: pathlib.Path) -> None:
    juv(["init", str(notebook)])
    juv(["add", str(notebook), "attrs"])
    process = juv(
        [
            "run",
            str(notebook),
            "--",
            "--port=8888",
            "--NotebookApp.token=''",
            "--NotebookApp.password=''",
        ],
        wait_and_check=False,
    )
    url = "http://localhost:8888/"
    wait_for_webserver(url)
    page.goto(url)
    expect(page.get_by_label("Main Content").get_by_text(notebook.name)).to_be_visible()
    # Menu
    page.get_by_text("File", exact=True).click()
    page.get_by_role("menu").get_by_text("Shut Down", exact=True).click()
    # Modal
    page.get_by_role("button", name="Shut Down").click()
    process.wait(10)
    assert notebook.exists()


def wait_for_webserver(url: str, timeout: int = 10) -> None:
    """Wait for webserver to be available"""
    start_time = time.time()
    while time.time() - start_time < timeout:
        try:
            with urllib.request.urlopen(url) as response:  # noqa: S310
                if response.status == 200:  # noqa: PLR2004
                    return
        except (urllib.error.URLError, urllib.error.HTTPError):
            pass
        time.sleep(0.2)
    msg = "web server did not start in time"
    raise RuntimeError(msg)
