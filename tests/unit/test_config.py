"""
Tests for core.config.Settings.

Covers the field validators (which enforce operational invariants) and the
derived database/redis URL construction, including password URL-encoding — a
real source of connection bugs when passwords contain special characters.
"""

import pytest
from pydantic import ValidationError

pytestmark = pytest.mark.unit


class TestEnvironmentValidation:
    def test_valid_environments_accepted(self, make_settings):
        for env in ["development", "staging", "production", "testing"]:
            assert make_settings(ENVIRONMENT=env).ENVIRONMENT == env

    def test_invalid_environment_rejected(self, make_settings):
        with pytest.raises(ValidationError):
            make_settings(ENVIRONMENT="banana")

    def test_is_production_and_is_development_flags(self, make_settings):
        prod = make_settings(ENVIRONMENT="production")
        assert prod.is_production is True
        assert prod.is_development is False

        dev = make_settings(ENVIRONMENT="development")
        assert dev.is_development is True
        assert dev.is_production is False

    def test_is_testing_true_when_testing_flag_set(self, make_settings):
        assert make_settings(ENVIRONMENT="development", TESTING=True).is_testing is True

    def test_is_testing_true_for_testing_environment(self, make_settings):
        assert make_settings(ENVIRONMENT="testing").is_testing is True


class TestLogLevelValidation:
    def test_log_level_is_uppercased(self, make_settings):
        assert make_settings(LOG_LEVEL="debug").LOG_LEVEL == "DEBUG"

    def test_invalid_log_level_rejected(self, make_settings):
        with pytest.raises(ValidationError):
            make_settings(LOG_LEVEL="chatty")


class TestNumericBoundsValidation:
    @pytest.mark.parametrize("value", [0, 101])
    def test_pool_size_out_of_range_rejected(self, make_settings, value):
        with pytest.raises(ValidationError):
            make_settings(DATABASE_POOL_SIZE=value)

    @pytest.mark.parametrize("value", [-1, 101])
    def test_max_overflow_out_of_range_rejected(self, make_settings, value):
        with pytest.raises(ValidationError):
            make_settings(DATABASE_MAX_OVERFLOW=value)

    @pytest.mark.parametrize("value", [0, 1441])
    def test_access_token_expiry_out_of_range_rejected(self, make_settings, value):
        with pytest.raises(ValidationError):
            make_settings(ACCESS_TOKEN_EXPIRE_MINUTES=value)

    @pytest.mark.parametrize("value", [0, 31])
    def test_refresh_token_expiry_out_of_range_rejected(self, make_settings, value):
        with pytest.raises(ValidationError):
            make_settings(REFRESH_TOKEN_EXPIRE_DAYS=value)


class TestDatabaseUrl:
    def test_supabase_async_url_uses_session_pooler(self, make_settings):
        s = make_settings(
            DATABASE_PROVIDER="supabase",
            SUPABASE_URL="https://abcdproj.supabase.co",
            SUPABASE_PASSWORD="simplepass",
        )
        url = s.database_url
        assert url.startswith("postgresql+asyncpg://")
        # Project ref becomes the pooler username suffix.
        assert "postgres.abcdproj:" in url
        assert "aws-0-ca-central-1.pooler.supabase.com:5432/postgres" in url

    def test_sync_url_uses_psycopg2_driver(self, make_settings):
        s = make_settings(
            DATABASE_PROVIDER="supabase",
            SUPABASE_URL="https://abcdproj.supabase.co",
            SUPABASE_PASSWORD="simplepass",
        )
        assert s.database_url_sync.startswith("postgresql+psycopg2://")

    def test_password_is_url_encoded(self, make_settings):
        """A password with '@' and a space must be percent-encoded or the DSN
        would be unparseable / point at the wrong host."""
        s = make_settings(
            DATABASE_PROVIDER="supabase",
            SUPABASE_URL="https://abcdproj.supabase.co",
            SUPABASE_PASSWORD="p@ss word",
        )
        assert "p%40ss+word" in s.database_url
        # The raw, unencoded password must never appear in the DSN.
        assert "p@ss word" not in s.database_url


class TestRedisUrl:
    def test_redis_url_without_password(self, make_settings):
        s = make_settings(REDIS_HOST="localhost", REDIS_PORT=6379, REDIS_DB=0)
        assert s.redis_url == "redis://localhost:6379/0"

    def test_redis_url_includes_password_when_set(self, make_settings):
        s = make_settings(
            REDIS_HOST="cache", REDIS_PORT=6379, REDIS_DB=1, REDIS_PASSWORD="secret"
        )
        assert s.redis_url == "redis://:secret@cache:6379/1"


class TestSecretKey:
    def test_effective_secret_key_prefers_secret_key(self, make_settings):
        s = make_settings(SECRET_KEY="explicit-secret", SUPABASE_JWT_SECRET="jwt")
        assert s.effective_secret_key == "explicit-secret"

    def test_effective_secret_key_falls_back_to_jwt_secret(self, make_settings):
        # SECRET_KEY shares an alias group with SUPABASE_JWT_SECRET, so pass the
        # fallback explicitly and leave SECRET_KEY unset.
        s = make_settings(SUPABASE_JWT_SECRET="jwt-fallback")
        assert s.effective_secret_key == "jwt-fallback"
