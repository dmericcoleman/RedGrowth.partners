import os
import sys
import socket
import subprocess
import time
import pytest
from playwright.sync_api import sync_playwright

DEFAULT_PORT = 8000
DEFAULT_HOST = "127.0.0.1"


def is_port_open(host: str, port: int) -> bool:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.settimeout(0.5)
        return s.connect_ex((host, port)) == 0


@pytest.fixture(scope="session")
def base_url():
    env_url = os.environ.get("BASE_URL")
    if env_url:
        yield env_url.rstrip("/")
        return

    port = int(os.environ.get("TEST_PORT", DEFAULT_PORT))
    host = DEFAULT_HOST
    server_process = None

    if not is_port_open(host, port):
        # Spawning local http.server from repository root
        repo_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        server_process = subprocess.Popen(
            [sys.executable, "-m", "http.server", str(port)],
            cwd=repo_root,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL
        )
        start_time = time.time()
        while time.time() - start_time < 8.0:
            if is_port_open(host, port):
                break
            time.sleep(0.1)
        else:
            raise RuntimeError(f"Local HTTP server failed to start on port {port}")

    url = f"http://{host}:{port}"
    yield url

    if server_process:
        server_process.terminate()
        try:
            server_process.wait(timeout=2.0)
        except Exception:
            server_process.kill()


@pytest.fixture(scope="session")
def browser_instance():
    with sync_playwright() as p:
        browser = p.chromium.launch(
            headless=True,
            args=["--no-sandbox", "--disable-setuid-sandbox", "--disable-dev-shm-usage"]
        )
        yield browser
        browser.close()


@pytest.fixture
def page(browser_instance, base_url):
    context = browser_instance.new_context(
        viewport={"width": 1280, "height": 800},
        user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
    )
    page = context.new_page()

    console_messages = []
    console_errors = []
    page_errors = []
    dialogs = []

    def handle_console(msg):
        console_messages.append(msg)
        if msg.type == "error":
            # Exclude expected 404s or analytics blockings if any, but capture everything
            console_errors.append(msg.text)

    def handle_pageerror(err):
        page_errors.append(str(err))

    def handle_dialog(dialog):
        dialogs.append({"type": dialog.type, "message": dialog.message})
        dialog.dismiss()

    page.on("console", handle_console)
    page.on("pageerror", handle_pageerror)
    page.on("dialog", handle_dialog)

    page._console_messages = console_messages
    page._console_errors = console_errors
    page._page_errors = page_errors
    page._dialogs = dialogs
    page._base_url = base_url

    yield page

    context.close()


def check_no_horizontal_overflow(page) -> tuple[bool, int, int]:
    """
    Evaluates whether document scrollWidth <= clientWidth.
    Returns (passes, scroll_width, client_width).
    """
    scroll_width = page.evaluate("() => document.documentElement.scrollWidth")
    client_width = page.evaluate("() => document.documentElement.clientWidth")
    return (scroll_width <= client_width, scroll_width, client_width)
