"""
NBA MCP Server Configuration

Configuration settings and environment variables for the MCP server.
"""

import os
from typing import Optional
from dataclasses import dataclass


@dataclass
class MCPConfig:
    """MCP Server configuration settings."""
    
    # Server settings
    server_name: str = "nba-pbp-server"
    server_version: str = "1.0.0"
    description: str = "NBA Play-by-Play Data MCP Server"
    
    # Database settings
    database_url: Optional[str] = None
    max_connections: int = 20
    min_connections: int = 5
    
    # Query settings
    max_query_timeout: int = 30  # seconds
    default_result_limit: int = 100
    max_result_limit: int = 1000
    
    # Natural language processing
    min_confidence_threshold: float = 0.3
    enable_fuzzy_matching: bool = True
    
    # Logging
    log_level: str = "INFO"
    enable_query_logging: bool = True
    
    @classmethod
    def from_environment(cls) -> "MCPConfig":
        """Create configuration from environment variables."""
        return cls(
            database_url=os.getenv("DATABASE_URL"),
            max_connections=int(os.getenv("MAX_DB_CONNECTIONS", "20")),
            min_connections=int(os.getenv("MIN_DB_CONNECTIONS", "5")),
            max_query_timeout=int(os.getenv("MAX_QUERY_TIMEOUT", "30")),
            default_result_limit=int(os.getenv("DEFAULT_RESULT_LIMIT", "100")),
            max_result_limit=int(os.getenv("MAX_RESULT_LIMIT", "1000")),
            min_confidence_threshold=float(os.getenv("MIN_CONFIDENCE", "0.3")),
            enable_fuzzy_matching=os.getenv("ENABLE_FUZZY_MATCHING", "true").lower() == "true",
            log_level=os.getenv("LOG_LEVEL", "INFO"),
            enable_query_logging=os.getenv("ENABLE_QUERY_LOGGING", "true").lower() == "true"
        )


# Global configuration instance
config = MCPConfig.from_environment()