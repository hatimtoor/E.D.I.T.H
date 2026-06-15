"""Stealth browser — the headline fix for Linux-server bot-blocking.

OpenClaw uses plain playwright-core with --headless=new and NO stealth; Hermes' good
option (Camoufox) is off by default / paywalled. E.D.I.T.H stacks every mitigation by
default: patched engine, JS fingerprint patches, proxy rotation, human cadence,
xvfb/headless handling, CAPTCHA detection, optional Camoufox backend.
"""
from edith.browser.stealth import StealthBrowser, StealthConfig, BrowserUnavailable

__all__ = ["StealthBrowser", "StealthConfig", "BrowserUnavailable"]
