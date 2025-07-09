"""
Configuration settings for CapitolScope application.

This module defines all application settings using Pydantic BaseSettings
with support for environment variables and validation.
"""

import os
from functools import lru_cache
from typing import Optional, List, Dict, Any

from pydantic import BaseSettings, Field, validator, PostgresDsn
from pydantic.types import SecretStr


class Settings(BaseSettings):
    """Application settings with environment variable support."""
    
    # Application
    APP_NAME: str = Field("CapitolScope", description="Application name")
    APP_VERSION: str = Field("1.0.0", description="Application version")
    DEBUG: bool = Field(False, description="Debug mode")
    ENVIRONMENT: str = Field("development", description="Environment (development/staging/production)")
    
    # API Configuration
    API_V1_PREFIX: str = Field("/api/v1", description="API v1 prefix")
    HOST: str = Field("0.0.0.0", description="Host to bind to")
    PORT: int = Field(8000, description="Port to bind to")
    RELOAD: bool = Field(True, description="Enable hot reload")
    
    # Security
    SECRET_KEY: SecretStr = Field(..., description="Secret key for JWT tokens")
    ALGORITHM: str = Field("HS256", description="JWT algorithm")
    ACCESS_TOKEN_EXPIRE_MINUTES: int = Field(30, description="Access token expiration minutes")
    REFRESH_TOKEN_EXPIRE_DAYS: int = Field(7, description="Refresh token expiration days")
    
    # Database Configuration
    DATABASE_HOST: str = Field(..., description="Database host")
    DATABASE_PORT: int = Field(5432, description="Database port")
    DATABASE_USER: str = Field(..., description="Database user")
    DATABASE_PASSWORD: SecretStr = Field(..., description="Database password")
    DATABASE_NAME: str = Field(..., description="Database name")
    DATABASE_ECHO: bool = Field(False, description="Enable SQLAlchemy echo")
    DATABASE_POOL_SIZE: int = Field(10, description="Database pool size")
    DATABASE_MAX_OVERFLOW: int = Field(20, description="Database max overflow")
    
    # Supabase Configuration
    SUPABASE_URL: str = Field(..., description="Supabase project URL")
    SUPABASE_ANON_KEY: SecretStr = Field(..., description="Supabase anonymous key")
    SUPABASE_SERVICE_ROLE_KEY: SecretStr = Field(..., description="Supabase service role key")
    
    # Redis Configuration
    REDIS_HOST: str = Field("localhost", description="Redis host")
    REDIS_PORT: int = Field(6379, description="Redis port")
    REDIS_DB: int = Field(0, description="Redis database")
    REDIS_PASSWORD: Optional[SecretStr] = Field(None, description="Redis password")
    REDIS_SSL: bool = Field(False, description="Redis SSL")
    
    # Celery Configuration
    CELERY_BROKER_URL: str = Field("redis://localhost:6379/0", description="Celery broker URL")
    CELERY_RESULT_BACKEND: str = Field("redis://localhost:6379/0", description="Celery result backend")
    
    # Logging Configuration
    LOG_LEVEL: str = Field("INFO", description="Log level")
    LOG_FORMAT: str = Field("%(asctime)s - %(name)s - %(levelname)s - %(message)s", description="Log format")
    
    # CORS Configuration
    CORS_ORIGINS: List[str] = Field(["*"], description="CORS allowed origins")
    CORS_METHODS: List[str] = Field(["GET", "POST", "PUT", "DELETE", "OPTIONS"], description="CORS allowed methods")
    CORS_HEADERS: List[str] = Field(["*"], description="CORS allowed headers")
    
    # Email Configuration (for notifications)
    EMAIL_HOST: Optional[str] = Field(None, description="Email SMTP host")
    EMAIL_PORT: Optional[int] = Field(587, description="Email SMTP port")
    EMAIL_USER: Optional[str] = Field(None, description="Email username")
    EMAIL_PASSWORD: Optional[SecretStr] = Field(None, description="Email password")
    EMAIL_FROM: Optional[str] = Field(None, description="Email from address")
    EMAIL_USE_TLS: bool = Field(True, description="Email use TLS")
    
    # External APIs
    ALPHA_VANTAGE_API_KEY: Optional[SecretStr] = Field(None, description="Alpha Vantage API key")
    POLYGON_API_KEY: Optional[SecretStr] = Field(None, description="Polygon API key")
    YAHOO_FINANCE_API_KEY: Optional[SecretStr] = Field(None, description="Yahoo Finance API key")
    
    # Social Media APIs
    TWITTER_API_KEY: Optional[SecretStr] = Field(None, description="Twitter API key")
    TWITTER_API_SECRET: Optional[SecretStr] = Field(None, description="Twitter API secret")
    LINKEDIN_CLIENT_ID: Optional[str] = Field(None, description="LinkedIn client ID")
    LINKEDIN_CLIENT_SECRET: Optional[SecretStr] = Field(None, description="LinkedIn client secret")
    
    # File Storage
    UPLOAD_FOLDER: str = Field("uploads", description="Upload folder path")
    MAX_UPLOAD_SIZE: int = Field(10 * 1024 * 1024, description="Max upload size in bytes")
    ALLOWED_EXTENSIONS: List[str] = Field(["jpg", "jpeg", "png", "gif", "pdf"], description="Allowed file extensions")
    
    # Pagination
    DEFAULT_PAGE_SIZE: int = Field(20, description="Default page size")
    MAX_PAGE_SIZE: int = Field(100, description="Maximum page size")
    
    # Rate Limiting
    RATE_LIMIT_ENABLED: bool = Field(True, description="Enable rate limiting")
    RATE_LIMIT_REQUESTS: int = Field(100, description="Rate limit requests per minute")
    RATE_LIMIT_WINDOW: int = Field(60, description="Rate limit window in seconds")
    
    # Caching
    CACHE_TTL: int = Field(300, description="Cache TTL in seconds")
    CACHE_ENABLED: bool = Field(True, description="Enable caching")
    
    # Monitoring
    SENTRY_DSN: Optional[str] = Field(None, description="Sentry DSN for error tracking")
    PROMETHEUS_METRICS: bool = Field(False, description="Enable Prometheus metrics")
    
    # Feature Flags
    FEATURE_SOCIAL_POSTING: bool = Field(True, description="Enable social media posting")
    FEATURE_ML_PREDICTIONS: bool = Field(False, description="Enable ML predictions")
    FEATURE_REAL_TIME_ALERTS: bool = Field(True, description="Enable real-time alerts")
    
    # Development/Testing
    TESTING: bool = Field(False, description="Testing mode")
    TEST_DATABASE_URL: Optional[str] = Field(None, description="Test database URL")
    
    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        case_sensitive = True
        
        # Environment variable prefixes
        env_prefix = ""
        
        # Field aliases for common environment variable names
        fields = {
            "SECRET_KEY": {"env": ["SECRET_KEY", "JWT_SECRET_KEY"]},
            "DATABASE_HOST": {"env": ["DATABASE_HOST", "DB_HOST", "SUPABASE_HOST"]},
            "DATABASE_PORT": {"env": ["DATABASE_PORT", "DB_PORT", "SUPABASE_PORT"]},
            "DATABASE_USER": {"env": ["DATABASE_USER", "DB_USER", "SUPABASE_USER"]},
            "DATABASE_PASSWORD": {"env": ["DATABASE_PASSWORD", "DB_PASSWORD", "SUPABASE_PASSWORD"]},
            "DATABASE_NAME": {"env": ["DATABASE_NAME", "DB_NAME", "SUPABASE_DATABASE"]},
        }
    
    @validator("ENVIRONMENT")
    def validate_environment(cls, v):
        """Validate environment value."""
        valid_envs = ["development", "staging", "production", "testing"]
        if v not in valid_envs:
            raise ValueError(f"Environment must be one of: {valid_envs}")
        return v
    
    @validator("LOG_LEVEL")
    def validate_log_level(cls, v):
        """Validate log level."""
        valid_levels = ["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"]
        if v.upper() not in valid_levels:
            raise ValueError(f"Log level must be one of: {valid_levels}")
        return v.upper()
    
    @validator("DATABASE_POOL_SIZE")
    def validate_pool_size(cls, v):
        """Validate database pool size."""
        if v < 1 or v > 100:
            raise ValueError("Database pool size must be between 1 and 100")
        return v
    
    @validator("DATABASE_MAX_OVERFLOW")
    def validate_max_overflow(cls, v):
        """Validate database max overflow."""
        if v < 0 or v > 100:
            raise ValueError("Database max overflow must be between 0 and 100")
        return v
    
    @validator("ACCESS_TOKEN_EXPIRE_MINUTES")
    def validate_access_token_expire(cls, v):
        """Validate access token expiration."""
        if v < 1 or v > 1440:  # 1 minute to 24 hours
            raise ValueError("Access token expiration must be between 1 and 1440 minutes")
        return v
    
    @validator("REFRESH_TOKEN_EXPIRE_DAYS")
    def validate_refresh_token_expire(cls, v):
        """Validate refresh token expiration."""
        if v < 1 or v > 30:  # 1 to 30 days
            raise ValueError("Refresh token expiration must be between 1 and 30 days")
        return v
    
    @property
    def database_url(self) -> str:
        """Get the database URL for SQLAlchemy."""
        return (
            f"postgresql+asyncpg://"
            f"{self.DATABASE_USER}:{self.DATABASE_PASSWORD.get_secret_value()}@"
            f"{self.DATABASE_HOST}:{self.DATABASE_PORT}/"
            f"{self.DATABASE_NAME}"
        )
    
    @property
    def database_url_sync(self) -> str:
        """Get the synchronous database URL for migrations."""
        return (
            f"postgresql://"
            f"{self.DATABASE_USER}:{self.DATABASE_PASSWORD.get_secret_value()}@"
            f"{self.DATABASE_HOST}:{self.DATABASE_PORT}/"
            f"{self.DATABASE_NAME}"
        )
    
    @property
    def redis_url(self) -> str:
        """Get the Redis URL."""
        auth = ""
        if self.REDIS_PASSWORD:
            auth = f":{self.REDIS_PASSWORD.get_secret_value()}@"
        
        protocol = "rediss" if self.REDIS_SSL else "redis"
        return f"{protocol}://{auth}{self.REDIS_HOST}:{self.REDIS_PORT}/{self.REDIS_DB}"
    
    @property
    def is_production(self) -> bool:
        """Check if running in production."""
        return self.ENVIRONMENT == "production"
    
    @property
    def is_development(self) -> bool:
        """Check if running in development."""
        return self.ENVIRONMENT == "development"
    
    @property
    def is_testing(self) -> bool:
        """Check if running in testing mode."""
        return self.TESTING or self.ENVIRONMENT == "testing"
    
    def get_database_config(self) -> Dict[str, Any]:
        """Get database configuration for SQLAlchemy."""
        return {
            "url": self.database_url,
            "echo": self.DATABASE_ECHO,
            "pool_size": self.DATABASE_POOL_SIZE,
            "max_overflow": self.DATABASE_MAX_OVERFLOW,
            "pool_pre_ping": True,
            "pool_recycle": 3600,
        }
    
    def get_redis_config(self) -> Dict[str, Any]:
        """Get Redis configuration."""
        return {
            "url": self.redis_url,
            "encoding": "utf-8",
            "decode_responses": True,
            "socket_connect_timeout": 5,
            "socket_timeout": 5,
            "retry_on_timeout": True,
        }
    
    def get_cors_config(self) -> Dict[str, Any]:
        """Get CORS configuration."""
        return {
            "allow_origins": self.CORS_ORIGINS,
            "allow_methods": self.CORS_METHODS,
            "allow_headers": self.CORS_HEADERS,
            "allow_credentials": True,
        }
    
    def get_logging_config(self) -> Dict[str, Any]:
        """Get logging configuration."""
        return {
            "version": 1,
            "disable_existing_loggers": False,
            "formatters": {
                "default": {
                    "format": self.LOG_FORMAT,
                    "datefmt": "%Y-%m-%d %H:%M:%S",
                },
                "access": {
                    "format": "%(asctime)s - %(name)s - %(levelname)s - %(message)s",
                },
            },
            "handlers": {
                "default": {
                    "formatter": "default",
                    "class": "logging.StreamHandler",
                    "stream": "ext://sys.stdout",
                },
                "access": {
                    "formatter": "access",
                    "class": "logging.StreamHandler",
                    "stream": "ext://sys.stdout",
                },
            },
            "loggers": {
                "": {
                    "level": self.LOG_LEVEL,
                    "handlers": ["default"],
                },
                "uvicorn.access": {
                    "handlers": ["access"],
                    "level": "INFO",
                    "propagate": False,
                },
            },
        }


@lru_cache()
def get_settings() -> Settings:
    """Get application settings (cached)."""
    return Settings()


# Global settings instance
settings = get_settings()


# Export for convenience
__all__ = ["settings", "get_settings", "Settings"] 