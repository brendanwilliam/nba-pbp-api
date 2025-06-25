#!/bin/bash
# NBA Play-by-Play API - Docker Build Script

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Configuration
IMAGE_TAG=${1:-latest}
REGISTRY=${DOCKER_REGISTRY:-""}
PROJECT_NAME="nba-pbp"

echo -e "${BLUE}🏀 NBA Play-by-Play API Docker Build${NC}"
echo -e "${BLUE}======================================${NC}"

# Function to print status
print_status() {
    echo -e "${GREEN}✅ $1${NC}"
}

print_warning() {
    echo -e "${YELLOW}⚠️  $1${NC}"
}

print_error() {
    echo -e "${RED}❌ $1${NC}"
}

# Check if Docker is running
if ! docker info > /dev/null 2>&1; then
    print_error "Docker is not running. Please start Docker and try again."
    exit 1
fi

print_status "Docker is running"

# Build API image
echo -e "\n${BLUE}📦 Building API image...${NC}"
if docker build -f Dockerfile.api -t ${PROJECT_NAME}-api:${IMAGE_TAG} .; then
    print_status "API image built successfully"
else
    print_error "Failed to build API image"
    exit 1
fi

# Build MCP image
echo -e "\n${BLUE}📦 Building MCP image...${NC}"
if docker build -f Dockerfile.mcp -t ${PROJECT_NAME}-mcp:${IMAGE_TAG} .; then
    print_status "MCP image built successfully"
else
    print_error "Failed to build MCP image"
    exit 1
fi

# Tag with registry if provided
if [ ! -z "$REGISTRY" ]; then
    echo -e "\n${BLUE}🏷️  Tagging images for registry...${NC}"
    docker tag ${PROJECT_NAME}-api:${IMAGE_TAG} ${REGISTRY}/${PROJECT_NAME}-api:${IMAGE_TAG}
    docker tag ${PROJECT_NAME}-mcp:${IMAGE_TAG} ${REGISTRY}/${PROJECT_NAME}-mcp:${IMAGE_TAG}
    print_status "Images tagged for registry: $REGISTRY"
fi

# Show image sizes
echo -e "\n${BLUE}📊 Image Information:${NC}"
echo "API Image:"
docker images ${PROJECT_NAME}-api:${IMAGE_TAG} --format "table {{.Repository}}\t{{.Tag}}\t{{.Size}}\t{{.CreatedAt}}"
echo "MCP Image:"
docker images ${PROJECT_NAME}-mcp:${IMAGE_TAG} --format "table {{.Repository}}\t{{.Tag}}\t{{.Size}}\t{{.CreatedAt}}"

# Security scan (if trivy is available)
if command -v trivy &> /dev/null; then
    echo -e "\n${BLUE}🔒 Running security scans...${NC}"
    
    echo "Scanning API image..."
    trivy image --exit-code 1 --severity HIGH,CRITICAL ${PROJECT_NAME}-api:${IMAGE_TAG} || print_warning "Security vulnerabilities found in API image"
    
    echo "Scanning MCP image..."
    trivy image --exit-code 1 --severity HIGH,CRITICAL ${PROJECT_NAME}-mcp:${IMAGE_TAG} || print_warning "Security vulnerabilities found in MCP image"
else
    print_warning "Trivy not installed. Skipping security scans."
    print_warning "Install trivy for security scanning: https://trivy.dev/"
fi

echo -e "\n${GREEN}🎉 Build completed successfully!${NC}"
echo -e "\n${BLUE}📝 Next steps:${NC}"
echo "• Run development environment: ${YELLOW}docker-compose up${NC}"
echo "• Run production environment: ${YELLOW}docker-compose -f docker-compose.prod.yml up${NC}"
echo "• Push to registry: ${YELLOW}docker push ${REGISTRY}/${PROJECT_NAME}-api:${IMAGE_TAG}${NC}"
echo "• Test API: ${YELLOW}curl http://localhost:8000/health${NC}"

# Optional: Run quick tests
read -p "$(echo -e ${BLUE}🧪 Run quick container tests? [y/N]: ${NC})" -n 1 -r
echo
if [[ $REPLY =~ ^[Yy]$ ]]; then
    echo -e "\n${BLUE}🧪 Running container tests...${NC}"
    
    # Test API container
    echo "Testing API container..."
    if docker run --rm -d --name test-api -p 8001:8000 ${PROJECT_NAME}-api:${IMAGE_TAG}; then
        sleep 5
        if curl -f http://localhost:8001/health > /dev/null 2>&1; then
            print_status "API container test passed"
        else
            print_warning "API container test failed"
        fi
        docker stop test-api
    fi
    
    # Test MCP container (basic run test)
    echo "Testing MCP container..."
    if timeout 10s docker run --rm ${PROJECT_NAME}-mcp:${IMAGE_TAG} python -c "print('MCP container can start')"; then
        print_status "MCP container test passed"
    else
        print_warning "MCP container test failed"
    fi
fi

echo -e "\n${GREEN}✨ All done! Images are ready for deployment.${NC}"