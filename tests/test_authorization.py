"""Security authorization gate: refuses out-of-scope, honors CIDR/glob/expiry."""
import pytest

from edith.security.authorization import (
    AuthorizationScope, OutOfScopeError, assert_in_scope,
)


def active_scope():
    return AuthorizationScope(
        engagement="lab", authorized_by="me@example.com", expires="2099-01-01",
        targets=["10.0.0.0/24", "*.lab.local", "127.0.0.1"],
    )


def test_no_scope_refuses_everything():
    with pytest.raises(OutOfScopeError):
        assert_in_scope("127.0.0.1", AuthorizationScope())


def test_in_scope_cidr_allowed():
    assert_in_scope("10.0.0.55", active_scope())  # no raise


def test_hostname_glob_allowed():
    assert_in_scope("box1.lab.local", active_scope())


def test_out_of_scope_refused():
    with pytest.raises(OutOfScopeError):
        assert_in_scope("8.8.8.8", active_scope())


def test_expired_scope_is_inactive():
    s = AuthorizationScope(engagement="old", authorized_by="me", expires="2000-01-01",
                           targets=["127.0.0.1"])
    assert not s.is_active()
    with pytest.raises(OutOfScopeError):
        assert_in_scope("127.0.0.1", s)
