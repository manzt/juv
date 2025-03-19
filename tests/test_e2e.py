from __future__ import annotations

import pathlib
import subprocess
import time
import typing

import pytest

pytest.importorskip("playwright")


if typing.TYPE_CHECKING:
    from playwright.sync_api import Page

SELF_DIR = pathlib.Path(__file__).parent
ROOT = SELF_DIR / ".."


@pytest.fixture(autouse=True)
def notebook() -> typing.Generator[pathlib.Path]:
    path = (ROOT / "smoke.ipynb").resolve()
    yield path
    path.unlink(missing_ok=True)


def juv(args: list[str], *, wait_and_check: bool = True) -> subprocess.Popen[str]:
    process = subprocess.Popen(  # noqa: S603
        ["uv", "run", "juv", *args],  # noqa: S607
        cwd=ROOT,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
    )
    if wait_and_check:
        exit_code = process.wait(2)
        if exit_code != 0:
            msg = f"juv command failed: {args}, exit code: {exit_code}"
            raise RuntimeError(msg)
    return process


def test_juv_run(page: Page, notebook: pathlib.Path) -> None:
    juv(["init", str(notebook)])
    juv(["add", str(notebook), "attrs"])
    process = juv(
        [
            "run",
            str(notebook),
            "--",
            "--host=127.0.0.1",
            "--port=8888",
            "--ServerApp.token=''",
            "--ServerApp.password=''",
            "--no-browser",
        ],
        wait_and_check=False,
    )
    # FIXME: nicer way to wait for the server to start  # noqa: FIX001, TD001, TD002, TD003
    time.sleep(2)
    if process.poll() is not None:
        msg = "OH NO" if process.stdout is None else process.stdout.readlines()
        raise ValueError(msg)
    url = "http://127.0.0.1:8888/lab"
    page.goto(url)
    # Menu
    page.get_by_text("File", exact=True).click()
    page.get_by_role("menu").get_by_text("Shut Down", exact=True).click()
    # Modal
    page.get_by_role("button", name="Shut Down").click()
    process.wait()
    assert notebook.exists()
