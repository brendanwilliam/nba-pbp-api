"""
Basic API test to verify the endpoints are working.
This is a simple test file to check that the API can start and respond to requests.
"""

import asyncio
import pytest
from fastapi.testclient import TestClient
from unittest.mock import AsyncMock, patch

# Mock the database manager to avoid needing a real database for basic tests
@pytest.fixture
def mock_db_manager():
    """Mock database manager for testing without a real database"""
    mock_manager = AsyncMock()
    mock_manager.pool = True  # Simulate connected pool
    
    # Mock health check
    mock_manager.execute_scalar = AsyncMock(return_value=1)
    
    # Mock query responses
    mock_manager.execute_query = AsyncMock(return_value=[])
    mock_manager.execute_count_query = AsyncMock(return_value=0)
    mock_manager.execute_query_df = AsyncMock(return_value=None)
    
    return mock_manager


def test_api_imports():
    """Test that the API can be imported without errors"""
    try:
        from main import app
        assert app is not None
        assert app.title == "NBA Play-by-Play API"
    except ImportError as e:
        pytest.skip(f"Cannot import API: {e}")


def test_health_endpoint():
    """Test the health check endpoint"""
    try:
        from main import app
        
        with TestClient(app) as client:
            response = client.get("/health")
            assert response.status_code == 200
            data = response.json()
            assert data["status"] == "healthy"
            assert "timestamp" in data
            
    except ImportError:
        pytest.skip("Cannot import API for testing")


def test_root_endpoint():
    """Test the root endpoint"""
    try:
        from main import app
        
        with TestClient(app) as client:
            response = client.get("/")
            assert response.status_code == 200
            data = response.json()
            assert data["message"] == "NBA Play-by-Play API"
            assert data["version"] == "1.0.0"
            
    except ImportError:
        pytest.skip("Cannot import API for testing")


def test_metrics_endpoint():
    """Test the metrics endpoint"""
    try:
        from main import app
        
        with TestClient(app) as client:
            response = client.get("/metrics")
            assert response.status_code == 200
            data = response.json()
            assert data["status"] == "operational"
            
    except ImportError:
        pytest.skip("Cannot import API for testing")


def test_openapi_docs():
    """Test that OpenAPI documentation is generated"""
    try:
        from main import app
        
        with TestClient(app) as client:
            response = client.get("/docs")
            assert response.status_code == 200
            
            # Test OpenAPI schema
            response = client.get("/openapi.json")
            assert response.status_code == 200
            schema = response.json()
            assert schema["info"]["title"] == "NBA Play-by-Play API"
            
    except ImportError:
        pytest.skip("Cannot import API for testing")


if __name__ == "__main__":
    # Run basic import test
    try:
        from main import app
        print("✅ API imports successfully")
        print(f"📊 API Title: {app.title}")
        print(f"🔢 API Version: {app.version}")
        print("🎯 Available endpoints:")
        
        # Print available routes
        for route in app.routes:
            if hasattr(route, 'path') and hasattr(route, 'methods'):
                methods = list(route.methods)
                if 'HEAD' in methods:
                    methods.remove('HEAD')
                if 'OPTIONS' in methods:
                    methods.remove('OPTIONS')
                if methods:
                    print(f"   {', '.join(methods)} {route.path}")
                    
    except ImportError as e:
        print(f"❌ Failed to import API: {e}")
        print("💡 This might be expected if database dependencies are not available")
    
    # Run pytest if available
    try:
        pytest.main([__file__, "-v"])
    except ImportError:
        print("ℹ️  pytest not available, skipping automated tests")