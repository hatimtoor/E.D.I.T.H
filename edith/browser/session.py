"""BrowserSession — a synchronous, persistent facade over the async StealthBrowser.

Lets the agent drive ONE browser across many tool calls (navigate -> read -> click -> type)
without managing asyncio. Runs a dedicated event loop in a background thread and submits
coroutines to it. `browser_factory` is injectable for tests (avoid launching real Chromium).
"""
from __future__ import annotations

import asyncio
import threading
from typing import Callable

from edith.browser.stealth import StealthBrowser, StealthConfig


class BrowserSession:
    def __init__(self, cfg: StealthConfig | None = None,
                 browser_factory: Callable[[StealthConfig], object] | None = None):
        self.cfg = cfg or StealthConfig()
        self._factory = browser_factory or StealthBrowser
        self._loop: asyncio.AbstractEventLoop | None = None
        self._thread: threading.Thread | None = None
        self._browser = None
        self._page = None

    # ── loop plumbing ───────────────────────────────────────────────
    def _ensure_loop(self) -> None:
        if self._loop is None:
            self._loop = asyncio.new_event_loop()
            self._thread = threading.Thread(target=self._loop.run_forever, daemon=True)
            self._thread.start()

    def _run(self, coro):
        self._ensure_loop()
        return asyncio.run_coroutine_threadsafe(coro, self._loop).result()

    async def _ensure_browser(self):
        if self._browser is None:
            self._browser = self._factory(self.cfg)
            await self._browser.start()

    # ── sync API (agent tools call these) ───────────────────────────
    def navigate(self, url: str) -> str:
        async def _go():
            await self._ensure_browser()
            self._page = await self._browser.goto(url)
            return await self._page.title()
        return self._run(_go())

    def read(self, selector: str = "body", max_chars: int = 6000) -> str:
        async def _r():
            if self._page is None:
                return "(no page — navigate first)"
            txt = await self._page.evaluate(
                "(sel) => { const e = document.querySelector(sel);"
                " return e ? (e.innerText || e.textContent || '') : ''; }", selector)
            return (txt or "")[:max_chars]
        return self._run(_r())

    def click(self, selector: str) -> str:
        async def _c():
            await self._browser.human_click(self._page, selector)
            return f"clicked {selector}"
        return self._run(_c())

    def type_text(self, selector: str, text: str) -> str:
        async def _t():
            await self._browser.human_type(self._page, selector, text)
            return f"typed into {selector}"
        return self._run(_t())

    def state(self) -> dict:
        async def _s():
            if self._page is None:
                return {"url": None, "title": None}
            return {"url": self._page.url, "title": await self._page.title()}
        return self._run(_s())

    def close(self) -> None:
        if self._browser is not None and self._loop is not None:
            try:
                self._run(self._browser.close())
            except Exception:
                pass
        if self._loop is not None:
            self._loop.call_soon_threadsafe(self._loop.stop)
            self._loop = None
