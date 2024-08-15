import os
import time
from http.client import HTTPConnection
from subprocess import Popen

import pytest

HOST = "localhost"
PORT = 8000
BASE_URL = f"http://{HOST}:{PORT}"


@pytest.fixture
def browser_context_args():
    return {"record_video_dir": "videos/"}


@pytest.fixture
def context(context):
    # We don't need a really long timeout.
    # The timeout determines how long Playwright waits for a HTML element to
    # become available.
    # By default it's 30 seconds, which is way too long when testing an app
    # locally.
    context.set_default_timeout(10000)
    yield context


@pytest.fixture
def mfa_app():
    """
    Running dev server and Playwright test in parallel.
    More info https://til.simonwillison.net/pytest/playwright-pytest
    """
    path = os.path.join(
        os.path.dirname(os.path.dirname(__file__)),
        "example_projects",
        "mfa_demo",
    )

    process = Popen(
        ["python", "-m", "main", "--reset-db"],
        cwd=path,
    )
    retries = 5
    while retries > 0:
        conn = HTTPConnection(f"{HOST}:{PORT}")
        try:
            conn.request("HEAD", "/")
            response = conn.getresponse()
            if response is not None:
                yield process
                break
        except ConnectionRefusedError:
            time.sleep(1)
            retries -= 1

    if not retries:
        raise RuntimeError("Failed to start http server")
    else:
        process.terminate()
        process.wait()
