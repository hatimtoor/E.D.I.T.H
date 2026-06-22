"""BrowserSession + browser tools — driven against a fake async browser (no real Chromium)."""
from edith.browser.session import BrowserSession
from edith.browser.stealth import StealthConfig


class _FakePage:
    url = "https://example.com/"
    async def title(self): return "Example"
    async def evaluate(self, js, *a):
        return "page body text" if a and a[0] == "body" else "el text"


class _FakeBrowser:
    def __init__(self, cfg): self.started = False; self.clicks = []; self.types = []
    async def start(self): self.started = True
    async def goto(self, url): self._url = url; return _FakePage()
    async def human_click(self, page, sel): self.clicks.append(sel)
    async def human_type(self, page, sel, text): self.types.append((sel, text))
    async def close(self): pass


def _session():
    return BrowserSession(StealthConfig(), browser_factory=_FakeBrowser)


def test_navigate_and_read():
    s = _session()
    assert "Example" == s.navigate("https://example.com")
    assert s.read("body") == "page body text"
    s.close()


def test_click_and_type_routed():
    s = _session()
    s.navigate("https://x")
    assert "clicked #btn" == s.click("#btn")
    assert "typed into #q" == s.type_text("#q", "hello")
    assert s._browser.clicks == ["#btn"] and s._browser.types == [("#q", "hello")]
    s.close()


def test_state_before_navigate():
    s = _session()
    assert s.state() == {"url": None, "title": None}
    s.close()


def test_browser_tools_registered(tmp_path):
    from edith.core.agent import Agent
    from edith.core.config import Config, MemoryConfig
    a = Agent(config=Config(home=str(tmp_path / "h"),
              memory=MemoryConfig(db_path=str(tmp_path / "h" / "m.sqlite"), embed_dim=128)))
    a.load_default_tools()
    for t in ("browser_navigate", "browser_read", "browser_click", "browser_type"):
        assert t in a.tools
    a.close()
