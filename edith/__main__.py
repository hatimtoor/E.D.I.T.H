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
skills_app = typer.Typer(help="Skill registry (progressive load + protection)")
memory_app = typer.Typer(help="3-layer memory")
sec_app = typer.Typer(help="Authorized-security toolkit")
app.add_typer(browser_app, name="browser")
app.add_typer(skills_app, name="skills")
app.add_typer(memory_app, name="memory")
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


@app.command()
def run(task: str):
    """Run a single task through the agent loop."""
    from edith.core.agent import Agent
    agent = Agent()
    try:
        con.print(Panel(agent.step(task), title="E.D.I.T.H"))
    finally:
        agent.close()


@app.command()
def chat():
    """Interactive chat session."""
    from edith.core.agent import Agent
    agent = Agent()
    con.print("[bold cyan]E.D.I.T.H online.[/] Ctrl-C to exit.")
    try:
        while True:
            user = con.input("[bold]you ›[/] ")
            if user.strip():
                con.print(Panel(agent.step(user), title="E.D.I.T.H"))
    except (KeyboardInterrupt, EOFError):
        con.print("\n[dim]session ended[/]")
    finally:
        agent.close()


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


if __name__ == "__main__":
    app()
