"""StealthBrowser — anti-block browser automation.

Degrades gracefully: if no engine is installed it raises BrowserUnavailable with install
guidance instead of crashing imports. The stealth strategy is engine-agnostic.
"""
from __future__ import annotations

import asyncio
import os
import platform
import random
from dataclasses import dataclass, field

_USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36",
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/130.0.0.0 Safari/537.36",
]

# Injected before any page script runs. Patches the exact signals OpenClaw leaves exposed.
_STEALTH_JS = r"""
(() => {
  // Each patch is isolated: a property the engine already locked (e.g. patchright
  // makes navigator.webdriver non-configurable) must not abort the remaining patches.
  const def = (obj, prop, getter) => {
    try { Object.defineProperty(obj, prop, { get: getter, configurable: true }); }
    catch (e) { /* already hardened by the engine — fine */ }
  };
  def(navigator, 'webdriver', () => undefined);
  def(navigator, 'plugins', () => [1, 2, 3, 4, 5]);
  def(navigator, 'languages', () => ['en-US', 'en']);
  try { if (!window.chrome) window.chrome = { runtime: {} }; } catch (e) {}
  try {
    const _q = window.navigator.permissions && window.navigator.permissions.query;
    if (_q) {
      window.navigator.permissions.query = (p) =>
        p && p.name === 'notifications'
          ? Promise.resolve({ state: Notification.permission })
          : _q(p);
    }
  } catch (e) {}
  try {
    const _gp = WebGLRenderingContext.prototype.getParameter;
    WebGLRenderingContext.prototype.getParameter = function (p) {
      if (p === 37445) return 'Intel Inc.';
      if (p === 37446) return 'Intel Iris OpenGL Engine';
      return _gp.call(this, p);
    };
  } catch (e) {}
})();
"""


class BrowserUnavailable(RuntimeError):
    pass


@dataclass
class StealthConfig:
    headless: bool = True
    engine: str = "patchright"          # patchright | playwright | camoufox
    proxy: str | None = None
    proxy_pool: list[str] = field(default_factory=list)
    captcha_key: str | None = None
    locale: str = "en-US"
    timezone: str = "America/New_York"
    min_delay_ms: int = 40
    max_delay_ms: int = 380
    user_agent: str | None = None


class StealthBrowser:
    """Async stealth browser. Use as `async with StealthBrowser(cfg) as b:`."""

    def __init__(self, cfg: StealthConfig | None = None):
        self.cfg = cfg or StealthConfig()
        self._pw = None
        self._browser = None
        self._context = None
        self._cm = None            # camoufox async ctx manager (if used)
        self._pages: list = []
        self._proxy_idx = 0

    async def __aenter__(self) -> "StealthBrowser":
        await self.start()
        return self

    async def __aexit__(self, *exc) -> None:
        await self.close()

    def _pick_proxy(self) -> str | None:
        # The #1 unblock factor: rotate residential proxies; never reuse a datacenter IP.
        if self.cfg.proxy_pool:
            p = self.cfg.proxy_pool[self._proxy_idx % len(self.cfg.proxy_pool)]
            self._proxy_idx += 1
            return p
        return self.cfg.proxy

    def _launch_args(self) -> list[str]:
        args = [
            "--no-first-run", "--no-default-browser-check",
            "--disable-blink-features=AutomationControlled",   # hides the automation flag
            "--disable-features=IsolateOrigins,site-per-process",
            "--disable-dev-shm-usage",                         # Linux/Docker stability
        ]
        if os.getenv("EDITH_NO_SANDBOX") or platform.system() == "Linux":
            args.append("--no-sandbox")
        return args

    async def start(self) -> None:
        try:
            if self.cfg.engine == "camoufox":
                await self._start_camoufox()
            else:
                await self._start_playwright(self.cfg.engine)
        except ImportError as e:
            raise BrowserUnavailable(
                f"browser engine '{self.cfg.engine}' not installed. "
                f"Run: python -m edith browser install. underlying: {e}") from e

    async def _start_playwright(self, engine: str) -> None:
        try:
            if engine == "patchright":
                from patchright.async_api import async_playwright  # type: ignore
            else:
                from playwright.async_api import async_playwright  # type: ignore
        except ImportError:
            from playwright.async_api import async_playwright  # type: ignore

        self._pw = await async_playwright().start()
        proxy = self._pick_proxy()
        launch_kw: dict = {"headless": self.cfg.headless, "args": self._launch_args()}
        if proxy:
            launch_kw["proxy"] = {"server": proxy}
        self._browser = await self._pw.chromium.launch(**launch_kw)
        self._context = await self._browser.new_context(
            user_agent=self.cfg.user_agent or random.choice(_USER_AGENTS),
            locale=self.cfg.locale, timezone_id=self.cfg.timezone,
            viewport={"width": random.choice([1280, 1366, 1440, 1536, 1920]),
                      "height": random.choice([720, 768, 800, 864, 1080])})
        await self._context.add_init_script(_STEALTH_JS)

    async def _start_camoufox(self) -> None:
        from camoufox.async_api import AsyncCamoufox  # type: ignore
        proxy = self._pick_proxy()
        self._cm = AsyncCamoufox(headless=self.cfg.headless,
                                 proxy={"server": proxy} if proxy else None,
                                 humanize=True, locale=self.cfg.locale)
        self._browser = await self._cm.__aenter__()
        self._context = await self._browser.new_context()

    async def close(self) -> None:
        for pg in self._pages:
            try:
                await pg.close()
            except Exception:
                pass
        try:
            if self._context:
                await self._context.close()
            if self._cm is not None:
                await self._cm.__aexit__(None, None, None)   # camoufox teardown
            elif self._browser:
                await self._browser.close()
            if self._pw:
                await self._pw.stop()
        except Exception:
            pass

    # ── human-like interaction ──────────────────────────────────────
    async def _jitter(self) -> None:
        await asyncio.sleep(random.randint(self.cfg.min_delay_ms, self.cfg.max_delay_ms) / 1000)

    async def goto(self, url: str):
        page = await self._context.new_page()
        self._pages.append(page)
        await self._jitter()
        await page.goto(url, wait_until="domcontentloaded")
        await self._maybe_handle_captcha(page)
        return page

    async def human_type(self, page, selector: str, text: str) -> None:
        # OpenClaw types at a fixed 75ms; real humans vary 40-220ms with pauses.
        await page.click(selector)
        for ch in text:
            await page.keyboard.type(ch)
            await asyncio.sleep(random.uniform(0.04, 0.22))
            if ch == " " and random.random() < 0.1:
                await asyncio.sleep(random.uniform(0.2, 0.5))

    async def human_click(self, page, selector: str) -> None:
        box = await page.locator(selector).bounding_box()
        if box:
            await page.mouse.move(box["x"] + box["width"] * random.uniform(0.2, 0.8),
                                  box["y"] + box["height"] * random.uniform(0.2, 0.8),
                                  steps=random.randint(5, 25))
            await self._jitter()
        await page.click(selector)

    async def fingerprint_report(self, page) -> dict:
        """Read back the spoofed signals — used to verify stealth actually applied."""
        return await page.evaluate(
            "() => ({ webdriver: navigator.webdriver, "
            "plugins: navigator.plugins.length, languages: navigator.languages, "
            "hasChrome: !!window.chrome })")

    # ── captcha ─────────────────────────────────────────────────────
    async def _maybe_handle_captcha(self, page) -> None:
        # DOM-based detection — only a REAL challenge (widget iframe or Cloudflare
        # interstitial) counts. Substring scans false-positive on normal pages whose
        # scripts merely mention "recaptcha"/"hcaptcha".
        is_captcha = await page.evaluate("""() => {
            const widget = document.querySelector(
              'iframe[src*="recaptcha"], iframe[src*="hcaptcha"], '
              + 'iframe[src*="turnstile"], iframe[title*="challenge"], '
              + '#challenge-form, #challenge-running, .cf-challenge, #cf-challenge-stage');
            const t = (document.title || '').toLowerCase();
            const cf = t.includes('just a moment') || t.includes('attention required');
            return !!(widget || cf);
        }""")
        if not is_captcha:
            return
        if not self.cfg.captcha_key:
            raise BrowserUnavailable(
                "CAPTCHA detected and no EDITH_CAPTCHA_KEY configured. Set a solver key or "
                "route through a residential proxy to avoid the challenge.")
        await self._solve_captcha(page)

    async def _solve_captcha(self, page) -> None:  # pragma: no cover - needs network
        raise NotImplementedError("captcha solver integration is a configured add-on")

    @staticmethod
    def preflight() -> list[str]:
        """Actionable warnings for what actually unblocks a Linux server."""
        warn: list[str] = []
        if platform.system() == "Linux":
            if not os.getenv("DISPLAY"):
                warn.append("No DISPLAY. For the hardest targets run headed under Xvfb: "
                            "`xvfb-run -a python -m edith ...` — new-headless is fingerprintable.")
            if not (os.getenv("EDITH_PROXY") or os.getenv("EDITH_PROXY_POOL")):
                warn.append("No proxy set. Datacenter IPs are the #1 block cause; configure a "
                            "residential proxy via EDITH_PROXY / EDITH_PROXY_POOL.")
        return warn
