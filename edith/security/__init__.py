"""Authorized-security toolkit. Every offensive action passes through
`assert_in_scope()`, which refuses any target not in a signed engagement scope.
Powerful for CTFs / authorized pentests / your own infra; safe-by-default otherwise.
"""
from edith.security.authorization import (
    AuthorizationScope, OutOfScopeError, assert_in_scope, load_scope,
)

__all__ = ["AuthorizationScope", "OutOfScopeError", "assert_in_scope", "load_scope"]
