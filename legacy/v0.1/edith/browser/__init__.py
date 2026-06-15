"""Stealth browser — the headline fix for Linux-server bot-blocking.

Why OpenClaw/Hermes get blocked on a Linux server (from reading their real code):
  * OpenClaw uses plain `playwright-core` with `--headless=new` and NO stealth:
    navigator.webdriver is exposed, CDP runtime leaks, no UA/locale/timezone
    spoofing, datacenter IP, fixed 75ms typing -> trivially fingerprinted.
  * Hermes can use Camoufox/Browserbase but they are optional / paywalled and
    off by default.

E.D.I.T.H stacks every mitigation by default:
  1. Patched engine (patchright) that removes the Runtime.enable / webdriver leaks.
  2. Optional Camoufox backend (fingerprint-hardened Firefox) like Hermes.
  3. JS patches injected pre-navigation (webdriver, plugins, languages, WebGL).
  4. Realistic UA + locale + timezone + viewport.
  5. Proxy rotation (residential pool) — the single biggest factor.
  6. Human cadence: randomized delays, mouse jitter, variable typing.
  7. Headless-on-Linux handled via Xvfb guidance + new-headless masking.
  8. CAPTCHA detection + optional solver fallback.
"""
from edith.browser.stealth import StealthBrowser, BrowserUnavailable

__all__ = ["StealthBrowser", "BrowserUnavailable"]
