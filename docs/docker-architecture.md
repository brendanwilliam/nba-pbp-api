# NBA Play-by-Play API - Docker Architecture

## Overview

The NBA Play-by-Play project uses a **multi-service Docker architecture** with separate containers for different components. This approach provides better scalability, security, and maintainability.

## Architecture Diagram

```
┌─────────────────────────────────────────────────────────────┐
│                        Load Balancer                        │
│                         (Nginx)                            │
│                        Port 80/443                         │
└─────────────────┬───────────────────────┬─────────────────┘
                  │                       │
         ┌────────▼────────┐    ┌────────▼────────┐
         │   NBA API       │    │   NBA MCP       │
         │   (FastAPI)     │    │   (MCP Server)  │
         │   Port 8000     │    │   Port 3000     │
         │   Public API    │    │   Private API   │
         └────────┬────────┘    └────────┬────────┘
                  │                      │
                  └──────────┬───────────┘
                             │
                    ┌────────▼────────┐
                    │   PostgreSQL    │
                    │   Port 5432     │
                    │   NBA Database  │
                    └─────────────────┘
```

## Service Breakdown

### 1. **NBA API Service** (`nba-api`)
- **Purpose**: Public-facing REST API
- **Technology**: FastAPI + Uvicorn
- **Port**: 8000
- **Scaling**: 3+ replicas in production
- **Features**:
  - Player, team, lineup statistics
  - Advanced querying and filtering
  - Statistical analysis
  - Rate limiting and authentication
  - OpenAPI documentation

### 2. **NBA MCP Service** (`nba-mcp`)
- **Purpose**: AI agent communication via MCP protocol
- **Technology**: Custom MCP server
- **Port**: 3000
- **Scaling**: 1-2 replicas typically sufficient
- **Features**:
  - Natural language to SQL conversion
  - AI agent integration
  - Private network communication
  - Optimized for agent workflows

### 3. **PostgreSQL Database** (`postgres`)
- **Purpose**: Primary data storage
- **Technology**: PostgreSQL 15
- **Port**: 5432
- **Features**:
  - NBA game and statistics data
  - Connection pooling
  - Backup and replication support

### 4. **Redis Cache** (`redis`)
- **Purpose**: Caching and session storage
- **Technology**: Redis 7
- **Port**: 6379
- **Features**:
  - API response caching
  - Rate limiting storage
  - Session management

### 5. **Nginx Load Balancer** (`nginx`)
- **Purpose**: Reverse proxy and load balancing
- **Technology**: Nginx
- **Ports**: 80 (HTTP), 443 (HTTPS)
- **Features**:
  - SSL termination
  - Load balancing
  - Rate limiting
  - Static file serving

## Container Images

### API Image (`Dockerfile.api`)
```dockerfile
FROM python:3.11-slim
# Multi-stage build for smaller image
# Includes: FastAPI, Pandas, NumPy, SciPy, scikit-learn
# Size: ~400MB (optimized)
```

### MCP Image (`Dockerfile.mcp`)
```dockerfile
FROM python:3.11-slim
# Lighter dependencies for MCP server
# Includes: MCP protocol, WebSockets, basic data processing
# Size: ~250MB (minimal)
```

## Environment Configurations

### Development (`docker-compose.yml`)
- **Hot reloading**: Source code mounted as volumes
- **Debug mode**: Enabled for both services
- **Database**: Local PostgreSQL container
- **Ports exposed**: All services accessible locally

### Production (`docker-compose.prod.yml`)
- **Optimized images**: No development dependencies
- **Health checks**: Comprehensive monitoring
- **Resource limits**: CPU and memory constraints
- **Logging**: Structured JSON logging
- **Secrets**: Environment-based configuration

## Deployment Strategies

### 1. **Development Setup**
```bash
# Build and start all services
docker-compose up --build

# Individual service management
docker-compose up api          # API only
docker-compose up mcp          # MCP only
docker-compose up postgres     # Database only
```

### 2. **Production Deployment**
```bash
# Build optimized images
./scripts/docker-build.sh

# Production deployment
docker-compose -f docker-compose.prod.yml up -d

# Scale API instances
docker-compose -f docker-compose.prod.yml up --scale api=5 -d
```

### 3. **Cloud Deployment**

#### Docker Swarm
```bash
# Initialize swarm
docker swarm init

# Deploy stack
docker stack deploy -c docker-compose.prod.yml nba-stack
```

#### Kubernetes
```bash
# Build and push images
docker build -t registry/nba-api:v1.0 -f Dockerfile.api .
docker build -t registry/nba-mcp:v1.0 -f Dockerfile.mcp .

# Deploy to Kubernetes
kubectl apply -f k8s/
```

## Service Communication

### Internal Network
- All services communicate on `nba_network`
- Service discovery via Docker DNS
- No external access to database/cache directly

### API → Database
```python
# Connection through internal network
DATABASE_URL = "postgresql://postgres:password@postgres:5432/nba_pbp"
```

### MCP → Database
```python
# Shared database access
DATABASE_URL = "postgresql://postgres:password@postgres:5432/nba_pbp"
```

### Nginx → Services
```nginx
upstream nba_api {
    server api:8000;  # Internal Docker network
}

upstream nba_mcp {
    server mcp:3000;  # Internal Docker network
}
```

## Security Considerations

### Network Isolation
- **Public**: Only Nginx (ports 80/443)
- **Internal**: API, MCP, Database, Redis
- **No direct database access** from outside

### Image Security
- **Non-root users**: All containers run as unprivileged users
- **Minimal base images**: Python slim images
- **Security scanning**: Trivy integration
- **Regular updates**: Automated dependency updates

### Secrets Management
```bash
# Environment-based secrets
export DATABASE_URL="postgresql://..."
export API_KEY_SECRET="..."
export REDIS_PASSWORD="..."

# Docker secrets (production)
echo "db_password" | docker secret create db_password -
```

## Monitoring and Observability

### Health Checks
```dockerfile
# API health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:8000/health || exit 1

# MCP health check  
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD python -c "import src.mcp.health_check" || exit 1
```

### Logging
```yaml
# Structured logging configuration
logging:
  driver: "json-file"
  options:
    max-size: "10m"
    max-file: "3"
```

### Metrics
- **Prometheus metrics**: `/metrics` endpoint
- **Application metrics**: Request count, response time, error rate
- **System metrics**: CPU, memory, disk usage

## Performance Optimization

### Resource Allocation
```yaml
# Production resource limits
deploy:
  resources:
    limits:
      memory: 512M
      cpus: '0.5'
    reservations:
      memory: 256M
      cpus: '0.25'
```

### Caching Strategy
- **Redis**: API response caching
- **Nginx**: Static content caching
- **Database**: Query result caching

### Auto-scaling
```yaml
# Docker Swarm auto-scaling
deploy:
  replicas: 3
  update_config:
    parallelism: 1
    delay: 10s
  restart_policy:
    condition: on-failure
```

## Best Practices

### 1. **Image Optimization**
- Multi-stage builds for smaller images
- Specific dependency versions
- Security scanning in CI/CD
- Regular base image updates

### 2. **Configuration Management**
- Environment-based configuration
- Secrets stored securely
- No hardcoded credentials
- Configuration validation

### 3. **Development Workflow**
```bash
# Local development
docker-compose up -d postgres redis  # Start dependencies
python src/api/start_api.py          # Run API locally
python src/mcp/server.py             # Run MCP locally

# Full containerized development
docker-compose up --build            # All services in containers
```

### 4. **Production Deployment**
```bash
# Build and test
./scripts/docker-build.sh
docker-compose -f docker-compose.prod.yml config  # Validate config

# Deploy with zero downtime
docker-compose -f docker-compose.prod.yml up -d --scale api=5
```

## Troubleshooting

### Common Issues

1. **Port conflicts**
   ```bash
   docker-compose down  # Stop all services
   docker system prune  # Clean up
   ```

2. **Database connection issues**
   ```bash
   docker-compose logs postgres  # Check database logs
   docker-compose exec postgres psql -U postgres -d nba_pbp  # Connect directly
   ```

3. **Image build failures**
   ```bash
   docker build --no-cache -f Dockerfile.api .  # Fresh build
   docker system df  # Check disk space
   ```

### Debugging
```bash
# Service logs
docker-compose logs api
docker-compose logs mcp
docker-compose logs postgres

# Container shell access
docker-compose exec api bash
docker-compose exec postgres psql -U postgres

# Resource usage
docker stats
docker-compose top
```

This Docker architecture provides a robust, scalable foundation for the NBA Play-by-Play API with clear separation of concerns and production-ready configurations.