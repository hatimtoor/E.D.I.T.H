"""Synchronous convenience wrappers around the async StealthBrowser.

Lets tools and CLI commands fetch/search the web in one call without managing an event
loop. All traffic goes through the stealth stack (so it survives bot-blocking).
"""
from __future__ import annotations

import asyncio

from edith.browser.stealth import StealthBrowser, StealthConfig


def _run(coro):
    return asyncio.run(coro)


def browse(url: str, *, cfg: StealthConfig | None = None, max_chars: int = 8000) -> dict:
    """Fetch a page through the stealth browser; return {url, title, text}."""
    async def _go():
        async with StealthBrowser(cfg or StealthConfig()) as b:
            page = await b.goto(url)
            title = await page.title()
            try:
                text = await page.inner_text("body")
            except Exception:
                text = await page.content()
            return {"url": url, "title": title, "text": text[:max_chars]}
    return _run(_go())


def search(query: str, *, cfg: StealthConfig | None = None, limit: int = 5) -> list[dict]:
    """Web search via DuckDuckGo's HTML endpoint, through the stealth browser.

    Returns a list of {title, url, snippet}. Uses the stealth stack so it isn't blocked.
    """
    async def _go():
        async with StealthBrowser(cfg or StealthConfig()) as b:
            page = await b.goto("https://www.bing.com/search?q=" + _q(query))
            # textContent (not innerText) — headless has no layout, so innerText is empty.
            results = await page.evaluate(
                r"""(limit) => {
                    const out = [];
                    document.querySelectorAll('li.b_algo').forEach(li => {
                      if (out.length >= limit) return;
                      const a = li.querySelector('h2 a');
                      const s = li.querySelector('.b_caption p') || li.querySelector('p');
                      if (a) out.push({title: (a.textContent || '').trim(), url: a.href,
                                       snippet: s ? (s.textContent || '').trim() : ''});
                    });
                    return out;
                }""", limit)
            for r in results:
                r["url"] = _decode_bing(r["url"])
            return results
    return _run(_go())


def _decode_bing(url: str) -> str:
    """Bing wraps result links in /ck/a?...&u=a1<base64url>. Decode to the real URL."""
    try:
        import base64
        from urllib.parse import urlparse, parse_qs
        if "bing.com/ck/a" not in url:
            return url
        u = parse_qs(urlparse(url).query).get("u", [None])[0]
        if u and u.startswith("a1"):
            b = u[2:] + "=" * (-len(u[2:]) % 4)
            return base64.urlsafe_b64decode(b).decode("utf-8", "replace")
    except Exception:
        pass
    return url


def _q(s: str) -> str:
    from urllib.parse import quote_plus
    return quote_plus(s)
