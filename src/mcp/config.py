"""
NBA MCP Server Configuration

Configuration settings and environment variables for the MCP server.
DEPRECATED: Use core.config.get_mcp_config() instead.
"""

import os
from typing import Optional
from dataclasses import dataclass
from ..core.config import get_mcp_config, get_database_config, get_config


@dataclass
class MCPConfig:
    """MCP Server configuration settings.
    
    DEPRECATED: Use core.config.MCPConfig instead.
    This class is kept for backward compatibility.
    """
    
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
        """Create configuration from environment variables.
        
        DEPRECATED: Use core.config.get_mcp_config() instead.
        """
        # Use the unified configuration system
        unified_config = get_config()
        mcp_config = unified_config.mcp
        db_config = unified_config.database
        
        return cls(
            database_url=db_config.get_connection_url(),
            max_connections=db_config.max_connections,
            min_connections=db_config.min_connections,
            max_query_timeout=mcp_config.max_query_timeout,
            default_result_limit=100,  # Default value
            max_result_limit=mcp_config.max_results,
            min_confidence_threshold=0.3,  # Default value
            enable_fuzzy_matching=True,  # Default value
            log_level=unified_config.log_level,
            enable_query_logging=mcp_config.enable_debug_logging
        )


# Global configuration instance (deprecated)
config = MCPConfig.from_environment()


# New recommended way to get MCP configuration
def get_mcp_server_config():
    """Get MCP server configuration using unified config system"""
    return get_mcp_config()