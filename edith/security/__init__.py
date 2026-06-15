"""Authorized-security toolkit.

Powerful but gated: every offensive action passes through `assert_in_scope()`, which
refuses any target not present in a signed engagement scope. This makes E.D.I.T.H a
serious tool for CTFs, authorized pentests, and your own infrastructure — and useless
for opportunistic abuse. Mass-targeting / worm / malicious-evasion behaviour is out of
scope by design.
"""
from edith.security.authorization import (
    AuthorizationScope,
    OutOfScopeError,
    assert_in_scope,
    load_scope,
)

__all__ = ["AuthorizationScope", "OutOfScopeError", "assert_in_scope", "load_scope"]
