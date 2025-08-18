"""
Unified configuration management for WNBA Play-by-Play scraping and database system.
Provides centralized configuration loading and validation.
"""

import os
from typing import Optional, Dict, Any, List
from dataclasses import dataclass
from pathlib import Path
from dotenv import load_dotenv


# Load environment variables from .env file
load_dotenv()


@dataclass
class DatabaseConfig:
    """Database configuration settings"""
    url: Optional[str] = None
    host: str = "localhost"
    port: int = 5432
    database: str = "wnba_pbp"
    user: str = "brendan"
    password: str = "postgres"
    min_connections: int = 5
    max_connections: int = 20
    command_timeout: int = 60
    application_name: str = "wnba_scraper_app"

    @classmethod
    def from_environment(cls) -> 'DatabaseConfig':
        """Load database configuration from environment variables"""
        # Try different environment variable names in priority order
        url = (
            os.getenv('DATABASE_URL') or
            os.getenv('NEON_DATABASE_URL') or
            os.getenv('POSTGRES_URL')
        )

        return cls(
            url=url,
            host=os.getenv('DB_HOST', 'localhost'),
            port=int(os.getenv('DB_PORT', '5432')),
            database=os.getenv('DB_NAME', 'wnba_pbp'),
            user=os.getenv('DB_USER', 'brendan'),
            password=os.getenv('DB_PASSWORD', 'postgres'),
            min_connections=int(os.getenv('DB_MIN_CONNECTIONS', '5')),
            max_connections=int(os.getenv('DB_MAX_CONNECTIONS', '20')),
            command_timeout=int(os.getenv('DB_COMMAND_TIMEOUT', '60')),
            application_name=os.getenv('DB_APPLICATION_NAME', 'wnba_scraper_app')
        )

    def get_connection_url(self) -> str:
        """Get the database connection URL"""
        if self.url:
            return self.url
        return f"postgresql://{self.user}:{self.password}@{self.host}:{self.port}/{self.database}"


@dataclass
class ScrapingConfig:
    """Scraping configuration settings"""
    rate_limit_delay: float = 1.0
    max_retries: int = 3
    timeout: int = 30
    concurrent_workers: int = 5
    user_agent: str = "WNBA-PBP-Scraper/1.0"

    @classmethod
    def from_environment(cls) -> 'ScrapingConfig':
        """Load scraping configuration from environment variables"""
        return cls(
            rate_limit_delay=float(os.getenv('SCRAPING_RATE_LIMIT_DELAY', '1.0')),
            max_retries=int(os.getenv('SCRAPING_MAX_RETRIES', '3')),
            timeout=int(os.getenv('SCRAPING_TIMEOUT', '30')),
            concurrent_workers=int(os.getenv('SCRAPING_CONCURRENT_WORKERS', '5')),
            user_agent=os.getenv('SCRAPING_USER_AGENT', 'WNBA-PBP-Scraper/1.0')
        )


@dataclass
class AnalyticsConfig:
    """Analytics configuration settings"""
    enable_possession_tracking: bool = True
    enable_lineup_tracking: bool = True
    possession_timeout_seconds: int = 24
    lineup_change_buffer_seconds: int = 2

    @classmethod
    def from_environment(cls) -> 'AnalyticsConfig':
        """Load analytics configuration from environment variables"""
        return cls(
            enable_possession_tracking=os.getenv('ANALYTICS_POSSESSION_TRACKING', 'true').lower() == 'true',
            enable_lineup_tracking=os.getenv('ANALYTICS_LINEUP_TRACKING', 'true').lower() == 'true',
            possession_timeout_seconds=int(os.getenv('ANALYTICS_POSSESSION_TIMEOUT', '24')),
            lineup_change_buffer_seconds=int(os.getenv('ANALYTICS_LINEUP_BUFFER', '2'))
        )


@dataclass
class UnifiedConfig:
    """Unified configuration for the entire WNBA PBP application"""
    database: DatabaseConfig
    scraping: ScrapingConfig
    analytics: AnalyticsConfig

    # Application-wide settings
    environment: str = "development"
    log_level: str = "INFO"
    project_root: Path = Path(__file__).parent.parent.parent

    @classmethod
    def from_environment(cls) -> 'UnifiedConfig':
        """Load all configuration from environment variables"""
        return cls(
            database=DatabaseConfig.from_environment(),
            scraping=ScrapingConfig.from_environment(),
            analytics=AnalyticsConfig.from_environment(),
            environment=os.getenv('ENVIRONMENT', 'development'),
            log_level=os.getenv('LOG_LEVEL', 'INFO'),
            project_root=Path(os.getenv('PROJECT_ROOT', Path(__file__).parent.parent.parent))
        )

    def is_production(self) -> bool:
        """Check if running in production environment"""
        return self.environment.lower() == 'production'

    def is_development(self) -> bool:
        """Check if running in development environment"""
        return self.environment.lower() == 'development'

    def is_testing(self) -> bool:
        """Check if running in testing environment"""
        return self.environment.lower() == 'testing'

    def get_log_config(self) -> Dict[str, Any]:
        """Get logging configuration dictionary"""
        return {
            'version': 1,
            'disable_existing_loggers': False,
            'formatters': {
                'standard': {
                    'format': '%(asctime)s [%(levelname)s] %(name)s: %(message)s'
                },
                'detailed': {
                    'format': '%(asctime)s [%(levelname)s] %(name)s:%(lineno)d: %(message)s'
                }
            },
            'handlers': {
                'default': {
                    'level': self.log_level,
                    'formatter': 'standard' if self.is_production() else 'detailed',
                    'class': 'logging.StreamHandler',
                    'stream': 'ext://sys.stdout'
                }
            },
            'loggers': {
                '': {
                    'handlers': ['default'],
                    'level': self.log_level,
                    'propagate': False
                },
                'wnba_pbp': {
                    'handlers': ['default'],
                    'level': self.log_level,
                    'propagate': False
                }
            }
        }

    def validate(self) -> List[str]:
        """Validate configuration and return list of validation errors"""
        errors = []

        # Database validation
        if not self.database.url and not all([
            self.database.host, 
            self.database.database, 
            self.database.user
        ]):
            errors.append("Database configuration incomplete: need URL or host/database/user")

        # Scraping validation
        if self.scraping.rate_limit_delay < 0:
            errors.append(f"Invalid scraping rate limit delay: {self.scraping.rate_limit_delay}")

        if self.scraping.max_retries < 0:
            errors.append(f"Invalid scraping max retries: {self.scraping.max_retries}")

        # Analytics validation
        if self.analytics.possession_timeout_seconds < 1:
            errors.append(f"Invalid possession timeout: {self.analytics.possession_timeout_seconds}")

        return errors

    def to_dict(self) -> Dict[str, Any]:
        """Convert configuration to dictionary for serialization"""
        return {
            'database': {
                'host': self.database.host,
                'port': self.database.port,
                'database': self.database.database,
                'user': self.database.user,
                'min_connections': self.database.min_connections,
                'max_connections': self.database.max_connections,
                'command_timeout': self.database.command_timeout,
                'application_name': self.database.application_name
            },
            'scraping': {
                'rate_limit_delay': self.scraping.rate_limit_delay,
                'max_retries': self.scraping.max_retries,
                'timeout': self.scraping.timeout,
                'concurrent_workers': self.scraping.concurrent_workers,
                'user_agent': self.scraping.user_agent
            },
            'analytics': {
                'enable_possession_tracking': self.analytics.enable_possession_tracking,
                'enable_lineup_tracking': self.analytics.enable_lineup_tracking,
                'possession_timeout_seconds': self.analytics.possession_timeout_seconds,
                'lineup_change_buffer_seconds': self.analytics.lineup_change_buffer_seconds
            },
            'environment': self.environment,
            'log_level': self.log_level,
            'project_root': str(self.project_root)
        }


# Global configuration instance
_global_config: Optional[UnifiedConfig] = None


def get_config() -> UnifiedConfig:
    """Get the global configuration instance"""
    global _global_config
    if _global_config is None:
        _global_config = UnifiedConfig.from_environment()
    return _global_config


def reload_config() -> UnifiedConfig:
    """Reload configuration from environment variables"""
    global _global_config
    _global_config = UnifiedConfig.from_environment()
    return _global_config


def validate_config() -> List[str]:
    """Validate the current configuration"""
    config = get_config()
    return config.validate()


# Convenience functions for specific configurations
def get_database_config() -> DatabaseConfig:
    """Get database configuration"""
    return get_config().database


def get_scraping_config() -> ScrapingConfig:
    """Get scraping configuration"""
    return get_config().scraping


def get_analytics_config() -> AnalyticsConfig:
    """Get analytics configuration"""
    return get_config().analytics


# Environment variable helpers
def get_env_bool(key: str, default: bool = False) -> bool:
    """Get boolean value from environment variable"""
    value = os.getenv(key, str(default)).lower()
    return value in ('true', '1', 'yes', 'on')


def get_env_int(key: str, default: int = 0) -> int:
    """Get integer value from environment variable"""
    try:
        return int(os.getenv(key, str(default)))
    except ValueError:
        return default


def get_env_float(key: str, default: float = 0.0) -> float:
    """Get float value from environment variable"""
    try:
        return float(os.getenv(key, str(default)))
    except ValueError:
        return default


def get_env_list(key: str, default: Optional[List[str]] = None, separator: str = ',') -> List[str]:
    """Get list value from environment variable"""
    if default is None:
        default = []

    value = os.getenv(key, separator.join(default))
    if not value:
        return default

    return [item.strip() for item in value.split(separator) if item.strip()]