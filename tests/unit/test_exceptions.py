"""Tests for the core exception hierarchy."""

import pytest

from core.exceptions import (
    AuthenticationError,
    AuthorizationError,
    CapitolScopeException,
    DatabaseError,
    ExternalAPIError,
    NotFoundError,
    RateLimitError,
    ValidationError,
)

pytestmark = pytest.mark.unit


class TestBaseException:
    def test_message_and_default_details(self):
        exc = CapitolScopeException("boom")
        assert exc.message == "boom"
        assert exc.details == {}
        assert str(exc) == "boom"

    def test_details_preserved(self):
        exc = CapitolScopeException("boom", details={"k": "v"})
        assert exc.details == {"k": "v"}

    def test_subclasses_are_catchable_as_base(self):
        with pytest.raises(CapitolScopeException):
            raise NotFoundError("Member", 42)


class TestNotFoundError:
    def test_message_composed_from_resource_and_identifier(self):
        exc = NotFoundError("Trade", "abc-123")
        assert exc.resource == "Trade"
        assert exc.identifier == "abc-123"
        assert "Trade" in exc.message and "abc-123" in exc.message


class TestSpecializedErrors:
    def test_validation_error_carries_field(self):
        exc = ValidationError("bad", field="ticker")
        assert exc.field == "ticker"

    def test_database_error_carries_operation(self):
        exc = DatabaseError("failed", operation="insert")
        assert exc.operation == "insert"

    def test_external_api_error_carries_api_metadata(self):
        exc = ExternalAPIError("timeout", api_name="yahoo", status_code=503)
        assert exc.api_name == "yahoo"
        assert exc.status_code == 503

    def test_rate_limit_error_carries_retry_after(self):
        exc = RateLimitError(retry_after=30)
        assert exc.retry_after == 30
        assert exc.message == "Rate limit exceeded"  # default message

    def test_auth_errors_have_sensible_defaults(self):
        assert AuthenticationError().message == "Authentication failed"
        assert AuthorizationError().message == "Access denied"
