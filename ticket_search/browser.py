import os
import time
import threading

from .config import BROWSER_USER_DATA_DIR, EXPERTFLYER_URL, TARGET_CLASSES
from .parser import extract_json_from_text, extract_flights_from_api

import json


class BrowserSession:
    """Manages a Playwright browser for intercepting ExpertFlyer API responses."""

    def __init__(self):
        self._playwright = None
        self._context = None
        self._page = None
        self._lock = threading.Lock()
        self._captured_raw: str | None = None

    def start(self):
        from playwright.sync_api import sync_playwright

        user_data = os.path.join(os.getcwd(), BROWSER_USER_DATA_DIR)
        os.makedirs(user_data, exist_ok=True)

        self._playwright = sync_playwright().start()
        self._context = self._playwright.chromium.launch_persistent_context(
            user_data_dir=user_data,
            headless=False,
            viewport={"width": 1280, "height": 900},
            args=["--disable-blink-features=AutomationControlled"],
        )

        if self._context.pages:
            self._page = self._context.pages[0]
        else:
            self._page = self._context.new_page()

        self._page.on("response", self._on_response)
        self._page.goto(EXPERTFLYER_URL, wait_until="domcontentloaded")

    def _on_response(self, response):
        """Intercept responses that contain ExpertFlyer search results."""
        if response.status != 200:
            return

        content_type = response.headers.get("content-type", "")
        if "text/" not in content_type and "json" not in content_type:
            return

        try:
            body = response.text()
        except Exception:
            return

        if "searchResults" not in body or "itineraries" not in body:
            return

        json_str = extract_json_from_text(body)
        if not json_str:
            return

        try:
            json.loads(json_str)
        except (json.JSONDecodeError, ValueError):
            return

        with self._lock:
            self._captured_raw = body
            print("\n    ✓ 检测到搜索结果（JSON 验证通过）")

    def wait_for_search(self, origin: str, dest: str) -> list[dict]:
        """Clear buffer and wait for user to perform a search in the browser."""
        with self._lock:
            self._captured_raw = None

        print(f"\n    请在浏览器中搜索 {origin}→{dest}，脚本将自动捕获结果...")
        print("    (输入 s 跳过此段用其他方式输入)")

        while True:
            with self._lock:
                raw = self._captured_raw

            if raw:
                flights = extract_flights_from_api(raw, origin, dest)
                with self._lock:
                    self._captured_raw = None
                if flights:
                    return flights
                cls_label = "/".join(TARGET_CLASSES)
                print(f"    ⚠ 响应中未找到 {origin}→{dest} 且{cls_label}舱有票的航班，请重新搜索或输入 s 跳过")

            try:
                self._page.wait_for_timeout(500)
            except Exception:
                pass

    def get_page(self):
        return self._page

    def close(self):
        if self._context:
            try:
                self._context.close()
            except Exception:
                pass
        if self._playwright:
            try:
                self._playwright.stop()
            except Exception:
                pass
