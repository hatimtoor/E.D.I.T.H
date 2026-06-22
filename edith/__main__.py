"""E.D.I.T.H command-line interface."""
from __future__ import annotations

import typer
from rich.console import Console
from rich.panel import Panel
from rich.table import Table

from edith import __version__
from edith.core.config import load_config

app = typer.Typer(help="E.D.I.T.H. — Even Dead, I'm The Hero. Autonomous local-first agent.",
                  no_args_is_help=True, add_completion=False)
browser_app = typer.Typer(help="Stealth browser controls")
web_app = typer.Typer(help="Direct web actions (no LLM key needed)")
skills_app = typer.Typer(help="Skill registry (progressive load + protection)")
memory_app = typer.Typer(help="3-layer memory")
sec_app = typer.Typer(help="Authorized-security toolkit")
app.add_typer(browser_app, name="browser")
app.add_typer(web_app, name="web")
app.add_typer(skills_app, name="skills")
app.add_typer(memory_app, name="memory")
sessions_app = typer.Typer(help="Persistent sessions + history search")
app.add_typer(sessions_app, name="sessions")
gateway_app = typer.Typer(help="Messaging gateway (Telegram/WhatsApp/... )")
app.add_typer(gateway_app, name="gateway")
app.add_typer(sec_app, name="security")

con = Console()


@app.command()
def version():
    """Show version."""
    con.print(f"E.D.I.T.H. v{__version__}")


@app.command()
def doctor():
    """Diagnose installed capabilities (green = ready)."""
    import importlib.util
    cfg = load_config()
    t = Table(title="E.D.I.T.H. doctor", header_style="bold")
    t.add_column("component"); t.add_column("status")

    def probe(mod: str) -> str:
        return "[green]ready[/]" if importlib.util.find_spec(mod) else "[yellow]not installed[/]"

    t.add_row("config", "[green]loaded[/]")
    t.add_row("model", cfg.model)
    t.add_row("LLM: anthropic", probe("anthropic"))
    t.add_row("LLM: openai", probe("openai"))
    t.add_row("browser: patchright", probe("patchright"))
    t.add_row("browser: playwright", probe("playwright"))
    t.add_row("browser: camoufox", probe("camoufox"))
    from edith.ruflo import RufloBridge
    t.add_row("ruflo", RufloBridge(enabled=cfg.ruflo.enabled).status())
    from edith.security import load_scope
    scope = load_scope(cfg.security.authorization_file)
    t.add_row("security scope", f"[green]active[/] ({scope.engagement})" if scope.is_active()
              else "[yellow]none[/] (offensive tools disabled)")
    con.print(t)


def _new_agent():
    """Build an agent with the full action-toolset loaded."""
    from edith.core.agent import Agent
    agent = Agent()
    agent.load_default_tools()
    return agent


def _explain_llm_error(e: Exception):
    from edith.core.llm import LLMError
    if isinstance(e, LLMError):
        con.print(f"[red]LLM unavailable:[/] {e}")
        con.print("[dim]Set a key (ANTHROPIC_API_KEY / OPENAI_API_KEY) or use a local model: "
                  "`EDITH_MODEL=ollama:llama3.1 python -m edith run \"...\"`. "
                  "See `python -m edith models`.[/]")
        return True
    return False


@app.command()
def run(task: str):
    """Run a single task through the agent loop (web, shell, memory, security tools wired in)."""
    agent = _new_agent()
    try:
        con.print(Panel(agent.step(task), title="E.D.I.T.H"))
    except Exception as e:
        if not _explain_llm_error(e):
            raise
    finally:
        agent.close()


@app.command()
def chat():
    """Interactive chat session with the full toolset."""
    agent = _new_agent()
    con.print("[bold cyan]E.D.I.T.H online.[/] Tools: web, memory, shell, security, files. Ctrl-C to exit.")
    try:
        while True:
            user = con.input("[bold]you ›[/] ")
            if user.strip():
                try:
                    con.print(Panel(agent.step(user), title="E.D.I.T.H"))
                except Exception as e:
                    if not _explain_llm_error(e):
                        raise
    except (KeyboardInterrupt, EOFError):
        con.print("\n[dim]session ended[/]")
    finally:
        agent.close()


@app.command()
def models():
    """Discover usable LLMs: cloud keys + local Ollama / LM Studio models."""
    import os
    t = Table(title="LLM providers", header_style="bold")
    t.add_column("provider"); t.add_column("status / models")
    t.add_row("anthropic", "[green]key set[/]" if os.getenv("ANTHROPIC_API_KEY") else "[dim]no key[/]")
    t.add_row("openai", "[green]key set[/]" if os.getenv("OPENAI_API_KEY") else "[dim]no key[/]")
    for name, url in (("ollama", "http://localhost:11434/api/tags"),
                      ("lmstudio", "http://localhost:1234/v1/models")):
        try:
            import urllib.request, json as _j
            with urllib.request.urlopen(url, timeout=2) as r:
                data = _j.loads(r.read().decode())
            if name == "ollama":
                tags = [m["name"] for m in data.get("models", [])][:8]
            else:
                tags = [m["id"] for m in data.get("data", [])][:8]
            t.add_row(name, "[green]running[/] " + (", ".join(tags) or "(no models pulled)"))
        except Exception:
            t.add_row(name, "[dim]not running[/]")
    con.print(t)
    con.print("[dim]Use one with:  EDITH_MODEL=ollama:<model> python -m edith run \"...\"[/]")


# ── browser ─────────────────────────────────────────────────────────
@browser_app.command("install")
def browser_install():
    """Install the stealth browser runtime (patchright + chromium)."""
    import subprocess, sys
    con.print("Installing patchright + chromium ...")
    subprocess.run([sys.executable, "-m", "pip", "install", "patchright"], check=False)
    subprocess.run([sys.executable, "-m", "patchright", "install", "chromium"], check=False)
    con.print("[green]done[/] (for hardest targets also: pip install camoufox && camoufox fetch)")


@browser_app.command("preflight")
def browser_preflight():
    """Check this host for the things that actually cause Linux-server blocking."""
    from edith.browser import StealthBrowser
    warns = StealthBrowser.preflight()
    if not warns:
        con.print("[green]preflight clean[/] — no obvious block triggers on this host")
    for w in warns:
        con.print(f"[yellow]⚠[/] {w}")


@browser_app.command("test")
def browser_test(url: str = typer.Argument("https://example.com")):
    """Open a URL with the stealth stack; report the title + spoofed fingerprint."""
    import asyncio
    from edith.browser import StealthBrowser, StealthConfig, BrowserUnavailable
    cfg = load_config()
    sc = StealthConfig(headless=cfg.browser.headless, engine=cfg.browser.engine,
                       proxy=cfg.browser.proxy, proxy_pool=cfg.browser.proxy_pool,
                       captcha_key=cfg.browser.captcha_key)

    async def _go():
        async with StealthBrowser(sc) as b:
            page = await b.goto(url)
            fp = await b.fingerprint_report(page)
            con.print(Panel(f"title: {await page.title()}\nfingerprint: {fp}", title=f"stealth -> {url}"))

    try:
        asyncio.run(_go())
    except BrowserUnavailable as e:
        con.print(f"[red]{e}[/]")


# ── skills ──────────────────────────────────────────────────────────
def _registry():
    from edith.skills import SkillRegistry
    return SkillRegistry(root=str(load_config().home_path / "skills"))


@skills_app.command("list")
def skills_list():
    reg = _registry()
    t = Table(title="skills"); t.add_column("name"); t.add_column("protected")
    for n in reg.names():
        t.add_row(n, "🔒" if reg._skills[n].protected else "")
    con.print(t)


@skills_app.command("protect")
def skills_protect(name: str):
    """Lock a skill so the agent's self-improvement loop can't overwrite it."""
    _registry().protect(name)
    con.print(f"[green]protected[/] {name} — agent can invoke but not modify")


@skills_app.command("unprotect")
def skills_unprotect(name: str):
    _registry().unprotect(name)
    con.print(f"[yellow]unprotected[/] {name}")


# ── memory ──────────────────────────────────────────────────────────
@memory_app.command("stats")
def memory_stats():
    from edith.memory import MemoryStore, MemoryLayer
    cfg = load_config()
    m = MemoryStore(cfg.memory.db_path, profile=cfg.memory.profile)
    t = Table(title=f"memory (profile={cfg.memory.profile})")
    t.add_column("layer"); t.add_column("count")
    for layer in MemoryLayer:
        t.add_row(layer.value, str(m.count(layer)))
    con.print(t)
    m.close()


# ── gateway ─────────────────────────────────────────────────────────
@gateway_app.command("channels")
def gateway_channels():
    """List every supported channel and whether it's live or planned."""
    import edith.gateway.channels  # noqa: registers live adapters
    from edith.gateway.registry import CHANNELS
    t = Table(title="messaging channels", header_style="bold")
    t.add_column("channel"); t.add_column("status"); t.add_column("transport"); t.add_column("needs")
    for name in sorted(CHANNELS, key=lambda n: (CHANNELS[n].status != "live", n)):
        s = CHANNELS[name]
        mark = "[green]live[/]" if s.status == "live" else "[dim]planned[/]"
        t.add_row(name, mark, s.transport, ", ".join(s.needs) or "-")
    con.print(t)


@gateway_app.command("run")
def gateway_run(channel: str = typer.Argument(..., help="live channel, e.g. telegram")):
    """Run the gateway for a channel (long-running; needs that channel's credentials)."""
    import edith.gateway.channels  # noqa
    from edith.gateway.registry import get_channel
    from edith.gateway.runtime import Gateway
    spec = get_channel(channel)
    if not spec or not spec.adapter:
        con.print(f"[red]no live adapter for '{channel}'[/] — see `edith gateway channels`")
        return
    ch = spec.adapter()
    if not ch.is_configured():
        con.print(f"[yellow]{channel} not configured[/] — set: {', '.join(spec.needs)}")
        return

    def make_agent(_key: str):
        from edith.core.agent import Agent
        a = Agent()
        a.load_default_tools()
        return a

    gw = Gateway(agent_factory=make_agent, channels=[ch])
    con.print(f"[green]gateway up[/] on {channel}. Ctrl-C to stop.")
    try:
        gw.run()
    except KeyboardInterrupt:
        con.print("\n[dim]gateway stopped[/]")
    finally:
        gw.close()


# ── sessions ────────────────────────────────────────────────────────
def _state_db():
    from edith.core.state import SessionDB
    return SessionDB(str(load_config().home_path / "state.sqlite"))


@sessions_app.command("list")
def sessions_list(limit: int = 20):
    """List recent persisted sessions."""
    import datetime as _dt
    d = _state_db()
    t = Table(title="sessions"); t.add_column("id"); t.add_column("source")
    t.add_column("msgs"); t.add_column("tokens(in/out)"); t.add_column("updated")
    for s in d.list_sessions(limit=limit):
        t.add_row(s.id, s.source, str(s.message_count),
                  f"{s.input_tokens}/{s.output_tokens}",
                  _dt.datetime.fromtimestamp(s.updated).strftime("%Y-%m-%d %H:%M"))
    con.print(t)
    d.close()


@sessions_app.command("search")
def sessions_search(query: str, limit: int = 15):
    """Full-text search across all past messages."""
    d = _state_db()
    hits = d.search(query, limit=limit)
    if not hits:
        con.print("[yellow]no matches[/]")
    for h in hits:
        con.print(f"[dim]{h['session_id']}[/] [bold]{h['role']}[/]: {h['content'][:160]}")
    d.close()


# ── security ────────────────────────────────────────────────────────
@sec_app.command("scope")
def security_scope():
    """Show the current authorization scope."""
    from edith.security import load_scope
    s = load_scope(load_config().security.authorization_file)
    if not s.is_active():
        con.print("[yellow]no active scope[/] — offensive tools disabled. "
                  "Create config/authorization.yaml (see config/authorization.example.yaml).")
        return
    con.print(Panel(f"engagement: {s.engagement}\nby: {s.authorized_by}\n"
                    f"expires: {s.expires}\ntargets: {s.targets}", title="authorization"))


@sec_app.command("scan")
def security_scan(target: str):
    """Authorized TCP port scan (refuses out-of-scope targets)."""
    from edith.security import load_scope
    from edith.security.recon import scan_ports
    from edith.security.authorization import OutOfScopeError
    scope = load_scope(load_config().security.authorization_file)
    try:
        rep = scan_ports(target, scope)
        con.print(Panel(f"ip: {rep.resolved_ip}\nopen ports: {rep.open_ports}\n"
                        f"tls: {rep.tls_info.get('protocol', '-')}", title=f"scan {target}"))
    except OutOfScopeError as e:
        con.print(f"[red]refused:[/] {e}")


# ── web (direct, no LLM key) ─────────────────────────────────────────
def _browser_cfg():
    b = load_config().browser
    from edith.browser.stealth import StealthConfig
    return StealthConfig(headless=b.headless, engine=b.engine, proxy=b.proxy,
                         proxy_pool=b.proxy_pool, captcha_key=b.captcha_key,
                         locale=b.locale, timezone=b.timezone)


@web_app.command("get")
def web_get(url: str, chars: int = 2000):
    """Fetch a page through the stealth browser and print its text."""
    from edith.browser.fetch import browse
    try:
        r = browse(url, cfg=_browser_cfg(), max_chars=chars)
        con.print(Panel(r["text"], title=f"{r['title']}  ({r['url']})"))
    except Exception as e:
        con.print(f"[red]error:[/] {type(e).__name__}: {e}")


@web_app.command("search")
def web_search_cmd(query: str, limit: int = 5):
    """Search the web (stealth, unblockable) and print results."""
    from edith.browser.fetch import search
    try:
        results = search(query, cfg=_browser_cfg(), limit=limit)
        if not results:
            con.print("[yellow]no results[/]")
            return
        for i, r in enumerate(results, 1):
            con.print(f"[bold]{i}. {r['title']}[/]\n   {r['url']}\n   [dim]{r.get('snippet','')}[/]")
    except Exception as e:
        con.print(f"[red]error:[/] {type(e).__name__}: {e}")


if __name__ == "__main__":
    app()
