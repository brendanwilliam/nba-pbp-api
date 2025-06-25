#!/bin/bash

# NBA Play-by-Play API Testing Script
# This script starts the API server and runs endpoint tests

set -e  # Exit on any error

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Configuration
API_PORT=${API_PORT:-8000}
API_HOST=${API_HOST:-localhost}
API_BASE_URL="http://${API_HOST}:${API_PORT}"
TEST_TIMEOUT=${TEST_TIMEOUT:-300}  # 5 minutes

echo -e "${BLUE}NBA Play-by-Play API Testing Suite${NC}"
echo "====================================="
echo "API URL: $API_BASE_URL"
echo "Test timeout: $TEST_TIMEOUT seconds"
echo ""

# Check if virtual environment is activated
if [[ "$VIRTUAL_ENV" == "" ]]; then
    echo -e "${YELLOW}Warning: Virtual environment not detected${NC}"
    echo "Please activate your virtual environment:"
    echo "  source venv/bin/activate"
    echo ""
fi

# Function to check if API is running
check_api_health() {
    echo -e "${BLUE}Checking API health...${NC}"
    
    for i in {1..30}; do
        if curl -s "$API_BASE_URL/health" > /dev/null 2>&1; then
            echo -e "${GREEN}✓ API is healthy and responding${NC}"
            return 0
        fi
        echo "Waiting for API to start... ($i/30)"
        sleep 2
    done
    
    echo -e "${RED}✗ API health check failed after 60 seconds${NC}"
    return 1
}

# Function to start API server
start_api() {
    echo -e "${BLUE}Starting API server...${NC}"
    
    # Check if API is already running
    if curl -s "$API_BASE_URL/health" > /dev/null 2>&1; then
        echo -e "${YELLOW}API server already running at $API_BASE_URL${NC}"
        return 0
    fi
    
    # Start API server in background
    cd "$(dirname "$0")/../.."  # Go to project root (two levels up from tests/api/)
    
    echo "Starting uvicorn server..."
    python -m uvicorn src.api.main:app --host 0.0.0.0 --port $API_PORT &
    API_PID=$!
    
    echo "API server started with PID: $API_PID"
    
    # Wait for API to be ready
    if check_api_health; then
        return 0
    else
        echo -e "${RED}Failed to start API server${NC}"
        kill $API_PID 2>/dev/null || true
        return 1
    fi
}

# Function to run API tests
run_tests() {
    echo -e "${BLUE}Running API endpoint tests...${NC}"
    
    cd "$(dirname "$0")"  # Stay in tests/api directory
    
    # Run the test script
    timeout $TEST_TIMEOUT python test_api_endpoints.py --base-url "$API_BASE_URL" --verbose
    
    return $?
}

# Function to cleanup
cleanup() {
    echo -e "${BLUE}Cleaning up...${NC}"
    
    if [[ ! -z "$API_PID" ]]; then
        echo "Stopping API server (PID: $API_PID)"
        kill $API_PID 2>/dev/null || true
        wait $API_PID 2>/dev/null || true
    fi
}

# Set trap for cleanup on exit
trap cleanup EXIT

# Main execution
main() {
    local start_server=true
    local run_tests_only=false
    
    # Parse command line arguments
    while [[ $# -gt 0 ]]; do
        case $1 in
            --no-start)
                start_server=false
                shift
                ;;
            --tests-only)
                run_tests_only=true
                start_server=false
                shift
                ;;
            --help)
                echo "Usage: $0 [OPTIONS]"
                echo ""
                echo "Options:"
                echo "  --no-start     Don't start API server (assume it's already running)"
                echo "  --tests-only   Only run tests (don't start or check API server)"
                echo "  --help         Show this help message"
                echo ""
                echo "Environment variables:"
                echo "  API_PORT       Port for API server (default: 8000)"
                echo "  API_HOST       Host for API server (default: localhost)"
                echo "  TEST_TIMEOUT   Test timeout in seconds (default: 300)"
                exit 0
                ;;
            *)
                echo -e "${RED}Unknown option: $1${NC}"
                echo "Use --help for usage information"
                exit 1
                ;;
        esac
    done
    
    # Start API server if requested
    if [[ "$start_server" == true ]]; then
        if ! start_api; then
            echo -e "${RED}Failed to start API server${NC}"
            exit 1
        fi
    elif [[ "$run_tests_only" == false ]]; then
        # Check if API is already running
        if ! check_api_health; then
            echo -e "${RED}API server is not running and --no-start was specified${NC}"
            echo "Please start the API server or remove --no-start flag"
            exit 1
        fi
    fi
    
    # Run tests
    if run_tests; then
        echo -e "${GREEN}✓ All API tests completed successfully!${NC}"
        exit 0
    else
        echo -e "${RED}✗ API tests failed${NC}"
        exit 1
    fi
}

# Run main function with all arguments
main "$@"