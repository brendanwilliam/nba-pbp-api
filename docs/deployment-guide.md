# NBA Play-by-Play API Deployment Guide

This guide covers recommended deployment strategies for the NBA Play-by-Play API across different environments and scales.

## Table of Contents
- [Deployment Options Overview](#deployment-options-overview)
- [Containerized Deployment (Recommended)](#containerized-deployment-recommended)
- [Cloud Platform Deployments](#cloud-platform-deployments)
- [Database Deployment](#database-deployment)
- [Production Configuration](#production-configuration)
- [Security Considerations](#security-considerations)
- [Monitoring and Observability](#monitoring-and-observability)
- [CI/CD Pipeline](#cicd-pipeline)

## Deployment Options Overview

### 1. **Containerized Deployment** (Recommended)
- **Best for**: Production environments, scalability, consistency
- **Technologies**: Docker, Kubernetes, Docker Compose
- **Pros**: Portable, scalable, consistent environments
- **Cons**: Requires container orchestration knowledge

### 2. **Cloud Platform as a Service**
- **Best for**: Quick deployment, managed infrastructure
- **Technologies**: Railway, Render, Heroku, Google Cloud Run
- **Pros**: Minimal ops overhead, auto-scaling
- **Cons**: Vendor lock-in, less control

### 3. **Virtual Private Server**
- **Best for**: Cost-effective, full control
- **Technologies**: DigitalOcean, Linode, AWS EC2
- **Pros**: Full control, cost-effective
- **Cons**: Manual ops management

### 4. **Serverless Functions**
- **Best for**: Event-driven workloads, cost optimization
- **Technologies**: AWS Lambda, Vercel, Netlify Functions
- **Pros**: Pay-per-use, auto-scaling
- **Cons**: Cold starts, execution time limits

## Containerized Deployment (Recommended)

### Docker Setup

#### 1. Create Dockerfile
```dockerfile
# src/api/Dockerfile
FROM python:3.11-slim

# Set environment variables
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

# Create app user
RUN addgroup --system --gid 1001 appgroup && \
    adduser --system --uid 1001 --gid 1001 --no-create-home appuser

# Set work directory
WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    gcc \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements and install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY src/ ./src/
COPY alembic.ini .
COPY alembic/ ./alembic/

# Change ownership of app files
RUN chown -R appuser:appgroup /app

# Switch to non-root user
USER appuser

# Expose port
EXPOSE 8000

# Health check
HEALTHCHECK --interval=30s --timeout=30s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:8000/health || exit 1

# Run the application
CMD ["uvicorn", "src.api.main:app", "--host", "0.0.0.0", "--port", "8000"]
```

#### 2. Create Docker Compose for Development
```yaml
# docker-compose.yml
version: '3.8'

services:
  api:
    build: 
      context: .
      dockerfile: src/api/Dockerfile
    ports:
      - "8000:8000"
    environment:
      - DATABASE_URL=postgresql://postgres:password@db:5432/nba_pbp
      - ENVIRONMENT=development
    depends_on:
      db:
        condition: service_healthy
    volumes:
      - ./src:/app/src  # Hot reload in development
    command: uvicorn src.api.main:app --host 0.0.0.0 --port 8000 --reload

  db:
    image: postgres:15
    environment:
      POSTGRES_DB: nba_pbp
      POSTGRES_USER: postgres
      POSTGRES_PASSWORD: password
    ports:
      - "5432:5432"
    volumes:
      - postgres_data:/var/lib/postgresql/data
      - ./sql/init.sql:/docker-entrypoint-initdb.d/init.sql
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U postgres"]
      interval: 10s
      timeout: 5s
      retries: 5

  redis:
    image: redis:7-alpine
    ports:
      - "6379:6379"
    command: redis-server --appendonly yes
    volumes:
      - redis_data:/data

volumes:
  postgres_data:
  redis_data:
```

#### 3. Production Docker Compose
```yaml
# docker-compose.prod.yml
version: '3.8'

services:
  api:
    build: 
      context: .
      dockerfile: src/api/Dockerfile
    restart: unless-stopped
    environment:
      - DATABASE_URL=${DATABASE_URL}
      - ENVIRONMENT=production
      - API_KEY_SECRET=${API_KEY_SECRET}
    depends_on:
      - redis
    deploy:
      replicas: 3
      resources:
        limits:
          memory: 512M
        reservations:
          memory: 256M

  nginx:
    image: nginx:alpine
    ports:
      - "80:80"
      - "443:443"
    volumes:
      - ./nginx.conf:/etc/nginx/nginx.conf
      - ./ssl:/etc/nginx/ssl
    depends_on:
      - api
    restart: unless-stopped

  redis:
    image: redis:7-alpine
    restart: unless-stopped
    command: redis-server --appendonly yes --requirepass ${REDIS_PASSWORD}
    volumes:
      - redis_data:/data

volumes:
  redis_data:
```

### Kubernetes Deployment

#### 1. Kubernetes Manifests
```yaml
# k8s/namespace.yaml
apiVersion: v1
kind: Namespace
metadata:
  name: nba-api

---
# k8s/configmap.yaml
apiVersion: v1
kind: ConfigMap
metadata:
  name: nba-api-config
  namespace: nba-api
data:
  ENVIRONMENT: "production"
  API_VERSION: "1.0.0"

---
# k8s/secret.yaml
apiVersion: v1
kind: Secret
metadata:
  name: nba-api-secrets
  namespace: nba-api
type: Opaque
stringData:
  DATABASE_URL: "postgresql://user:password@db:5432/nba_pbp"
  API_KEY_SECRET: "your-secret-key"
  REDIS_PASSWORD: "redis-password"

---
# k8s/deployment.yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: nba-api
  namespace: nba-api
spec:
  replicas: 3
  selector:
    matchLabels:
      app: nba-api
  template:
    metadata:
      labels:
        app: nba-api
    spec:
      containers:
      - name: api
        image: nba-api:latest
        ports:
        - containerPort: 8000
        env:
        - name: DATABASE_URL
          valueFrom:
            secretKeyRef:
              name: nba-api-secrets
              key: DATABASE_URL
        - name: API_KEY_SECRET
          valueFrom:
            secretKeyRef:
              name: nba-api-secrets
              key: API_KEY_SECRET
        envFrom:
        - configMapRef:
            name: nba-api-config
        livenessProbe:
          httpGet:
            path: /health
            port: 8000
          initialDelaySeconds: 30
          periodSeconds: 10
        readinessProbe:
          httpGet:
            path: /health
            port: 8000
          initialDelaySeconds: 5
          periodSeconds: 5
        resources:
          requests:
            memory: "256Mi"
            cpu: "250m"
          limits:
            memory: "512Mi"
            cpu: "500m"

---
# k8s/service.yaml
apiVersion: v1
kind: Service
metadata:
  name: nba-api-service
  namespace: nba-api
spec:
  selector:
    app: nba-api
  ports:
  - port: 80
    targetPort: 8000
  type: ClusterIP

---
# k8s/ingress.yaml
apiVersion: networking.k8s.io/v1
kind: Ingress
metadata:
  name: nba-api-ingress
  namespace: nba-api
  annotations:
    kubernetes.io/ingress.class: nginx
    cert-manager.io/cluster-issuer: letsencrypt-prod
    nginx.ingress.kubernetes.io/rate-limit: "100"
spec:
  tls:
  - hosts:
    - api.nba-pbp.com
    secretName: nba-api-tls
  rules:
  - host: api.nba-pbp.com
    http:
      paths:
      - path: /
        pathType: Prefix
        backend:
          service:
            name: nba-api-service
            port:
              number: 80
```

## Cloud Platform Deployments

### 1. Railway (Recommended for simplicity)

#### railway.toml
```toml
[build]
builder = "nixpacks"

[deploy]
healthcheckPath = "/health"
healthcheckTimeout = 300
restartPolicyType = "on-failure"
restartPolicyMaxRetries = 3

[[deploy.env]]
name = "PORT"
value = "8000"

[[deploy.env]]
name = "ENVIRONMENT"
value = "production"
```

#### Steps:
1. Connect GitHub repository to Railway
2. Add PostgreSQL plugin
3. Set environment variables
4. Deploy automatically on push

### 2. Google Cloud Run

#### cloudbuild.yaml
```yaml
steps:
  # Build the container image
  - name: 'gcr.io/cloud-builders/docker'
    args: ['build', '-t', 'gcr.io/$PROJECT_ID/nba-api:$COMMIT_SHA', '-f', 'src/api/Dockerfile', '.']

  # Push the container image to Container Registry
  - name: 'gcr.io/cloud-builders/docker'
    args: ['push', 'gcr.io/$PROJECT_ID/nba-api:$COMMIT_SHA']

  # Deploy container image to Cloud Run
  - name: 'gcr.io/google.com/cloudsdktool/cloud-sdk'
    entrypoint: gcloud
    args:
    - 'run'
    - 'deploy'
    - 'nba-api'
    - '--image'
    - 'gcr.io/$PROJECT_ID/nba-api:$COMMIT_SHA'
    - '--region'
    - 'us-central1'
    - '--platform'
    - 'managed'
    - '--allow-unauthenticated'
    - '--set-env-vars'
    - 'DATABASE_URL=$$DATABASE_URL'
    - '--memory'
    - '512Mi'
    - '--concurrency'
    - '100'
    - '--max-instances'
    - '10'

substitutions:
  _SERVICE_NAME: nba-api

options:
  substitution_option: ALLOW_LOOSE
```

### 3. AWS ECS/Fargate

#### Task Definition
```json
{
  "family": "nba-api",
  "networkMode": "awsvpc",
  "requiresCompatibilities": ["FARGATE"],
  "cpu": "512",
  "memory": "1024",
  "executionRoleArn": "arn:aws:iam::account:role/ecsTaskExecutionRole",
  "taskRoleArn": "arn:aws:iam::account:role/ecsTaskRole",
  "containerDefinitions": [
    {
      "name": "nba-api",
      "image": "account.dkr.ecr.region.amazonaws.com/nba-api:latest",
      "portMappings": [
        {
          "containerPort": 8000,
          "protocol": "tcp"
        }
      ],
      "environment": [
        {
          "name": "ENVIRONMENT",
          "value": "production"
        }
      ],
      "secrets": [
        {
          "name": "DATABASE_URL",
          "valueFrom": "arn:aws:secretsmanager:region:account:secret:nba-api-db-url"
        }
      ],
      "logConfiguration": {
        "logDriver": "awslogs",
        "options": {
          "awslogs-group": "/ecs/nba-api",
          "awslogs-region": "us-east-1",
          "awslogs-stream-prefix": "ecs"
        }
      },
      "healthCheck": {
        "command": ["CMD-SHELL", "curl -f http://localhost:8000/health || exit 1"],
        "interval": 30,
        "timeout": 5,
        "retries": 3
      }
    }
  ]
}
```

## Database Deployment

### 1. Managed Database Services (Recommended)

#### Neon (Serverless PostgreSQL)
```bash
# Set up Neon database
export NEON_DATABASE_URL="postgresql://user:password@endpoint.neon.tech/nba_pbp"

# Run migrations
alembic upgrade head
```

#### AWS RDS
```terraform
# terraform/rds.tf
resource "aws_db_instance" "nba_api_db" {
  identifier = "nba-api-db"
  
  engine         = "postgres"
  engine_version = "15.4"
  instance_class = "db.t3.micro"
  
  allocated_storage     = 20
  max_allocated_storage = 100
  storage_type         = "gp2"
  storage_encrypted    = true
  
  db_name  = "nba_pbp"
  username = "nba_api_user"
  password = var.db_password
  
  vpc_security_group_ids = [aws_security_group.db.id]
  db_subnet_group_name   = aws_db_subnet_group.main.name
  
  backup_retention_period = 7
  backup_window          = "03:00-04:00"
  maintenance_window     = "Mon:04:00-Mon:05:00"
  
  skip_final_snapshot = false
  final_snapshot_identifier = "nba-api-db-final-snapshot"
  
  tags = {
    Name = "NBA API Database"
    Environment = "production"
  }
}
```

### 2. Self-Hosted Database

#### Docker Compose with PostgreSQL
```yaml
version: '3.8'
services:
  postgres:
    image: postgres:15
    restart: unless-stopped
    environment:
      POSTGRES_DB: nba_pbp
      POSTGRES_USER: nba_api_user
      POSTGRES_PASSWORD: ${DB_PASSWORD}
    volumes:
      - postgres_data:/var/lib/postgresql/data
      - ./backups:/backups
    ports:
      - "5432:5432"
    command: >
      postgres
      -c shared_preload_libraries=pg_stat_statements
      -c pg_stat_statements.track=all
      -c max_connections=200
      -c shared_buffers=256MB
      -c effective_cache_size=1GB
      -c work_mem=4MB

volumes:
  postgres_data:
```

## Production Configuration

### 1. Environment Variables
```bash
# Production environment file (.env.prod)
ENVIRONMENT=production
DATABASE_URL=postgresql://user:password@host:5432/nba_pbp
REDIS_URL=redis://user:password@host:6379/0

# Security
API_KEY_SECRET=your-super-secret-key
ALLOWED_HOSTS=api.nba-pbp.com,nba-api.herokuapp.com

# Performance
DATABASE_POOL_SIZE=20
DATABASE_MAX_OVERFLOW=30
REDIS_POOL_SIZE=10

# Monitoring
SENTRY_DSN=https://your-sentry-dsn
LOG_LEVEL=INFO
```

### 2. Application Configuration
```python
# src/api/config.py
import os
from functools import lru_cache
from pydantic import BaseSettings

class Settings(BaseSettings):
    environment: str = "development"
    database_url: str
    redis_url: str = None
    
    # Security
    api_key_secret: str
    allowed_hosts: list[str] = ["*"]
    
    # Performance
    database_pool_size: int = 20
    database_max_overflow: int = 30
    query_timeout: int = 60
    
    # Monitoring
    sentry_dsn: str = None
    log_level: str = "INFO"
    
    class Config:
        env_file = ".env"

@lru_cache()
def get_settings():
    return Settings()
```

### 3. Nginx Configuration
```nginx
# nginx.conf
upstream nba_api {
    server api:8000;
}

server {
    listen 80;
    server_name api.nba-pbp.com;
    return 301 https://$server_name$request_uri;
}

server {
    listen 443 ssl http2;
    server_name api.nba-pbp.com;
    
    ssl_certificate /etc/nginx/ssl/cert.pem;
    ssl_certificate_key /etc/nginx/ssl/key.pem;
    
    # Security headers
    add_header X-Frame-Options "SAMEORIGIN" always;
    add_header X-XSS-Protection "1; mode=block" always;
    add_header X-Content-Type-Options "nosniff" always;
    add_header Strict-Transport-Security "max-age=31536000; includeSubDomains" always;
    
    # Rate limiting
    limit_req_zone $binary_remote_addr zone=api:10m rate=10r/s;
    
    location / {
        limit_req zone=api burst=20 nodelay;
        
        proxy_pass http://nba_api;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        
        # Timeouts
        proxy_connect_timeout 30s;
        proxy_send_timeout 30s;
        proxy_read_timeout 30s;
    }
    
    location /health {
        proxy_pass http://nba_api;
        access_log off;
    }
}
```

## Security Considerations

### 1. API Security
```python
# src/api/middleware/security.py
from fastapi import FastAPI, Request, HTTPException
from fastapi.middleware.trustedhost import TrustedHostMiddleware
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded

def add_security_middleware(app: FastAPI):
    # Rate limiting
    limiter = Limiter(key_func=get_remote_address)
    app.state.limiter = limiter
    app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)
    
    # Trusted hosts
    app.add_middleware(
        TrustedHostMiddleware, 
        allowed_hosts=["api.nba-pbp.com", "localhost"]
    )
    
    # API key authentication
    @app.middleware("http")
    async def api_key_middleware(request: Request, call_next):
        if request.url.path in ["/health", "/metrics", "/docs", "/openapi.json"]:
            response = await call_next(request)
            return response
            
        api_key = request.headers.get("X-API-Key")
        if not api_key or not validate_api_key(api_key):
            raise HTTPException(status_code=401, detail="Invalid API key")
            
        response = await call_next(request)
        return response
```

### 2. Database Security
- Use connection pooling with SSL
- Enable row-level security
- Regular security updates
- Backup encryption
- Network isolation

### 3. Infrastructure Security
```yaml
# Security scanning in CI/CD
- name: Run Trivy vulnerability scanner
  uses: aquasecurity/trivy-action@master
  with:
    image-ref: 'nba-api:latest'
    format: 'sarif'
    output: 'trivy-results.sarif'
```

## Monitoring and Observability

### 1. Application Monitoring
```python
# src/api/monitoring.py
import time
from prometheus_client import Counter, Histogram, generate_latest, CONTENT_TYPE_LATEST
from fastapi import Request, Response

REQUEST_COUNT = Counter('http_requests_total', 'Total HTTP requests', ['method', 'endpoint', 'status'])
REQUEST_DURATION = Histogram('http_request_duration_seconds', 'HTTP request duration')

@app.middleware("http")
async def add_prometheus_middleware(request: Request, call_next):
    start_time = time.time()
    response = await call_next(request)
    duration = time.time() - start_time
    
    REQUEST_COUNT.labels(
        method=request.method,
        endpoint=request.url.path,
        status=response.status_code
    ).inc()
    REQUEST_DURATION.observe(duration)
    
    return response

@app.get("/metrics")
async def metrics():
    return Response(generate_latest(), media_type=CONTENT_TYPE_LATEST)
```

### 2. Logging Configuration
```python
# src/api/logging_config.py
import logging
import sys
from pythonjsonlogger import jsonlogger

def setup_logging():
    logHandler = logging.StreamHandler(sys.stdout)
    formatter = jsonlogger.JsonFormatter(
        fmt='%(asctime)s %(name)s %(levelname)s %(message)s'
    )
    logHandler.setFormatter(formatter)
    
    logger = logging.getLogger()
    logger.addHandler(logHandler)
    logger.setLevel(logging.INFO)
    
    # Reduce noise from libraries
    logging.getLogger("uvicorn.access").setLevel(logging.WARNING)
    logging.getLogger("asyncpg").setLevel(logging.WARNING)
```

### 3. Health Checks
```python
# Enhanced health check
@app.get("/health")
async def health_check():
    health_status = {
        "status": "healthy",
        "timestamp": datetime.utcnow().isoformat(),
        "version": "1.0.0",
        "checks": {}
    }
    
    # Database check
    try:
        await db_manager.health_check()
        health_status["checks"]["database"] = "healthy"
    except Exception as e:
        health_status["checks"]["database"] = f"unhealthy: {str(e)}"
        health_status["status"] = "unhealthy"
    
    # Redis check (if used)
    try:
        # Redis health check
        health_status["checks"]["redis"] = "healthy"
    except:
        health_status["checks"]["redis"] = "unhealthy"
    
    status_code = 200 if health_status["status"] == "healthy" else 503
    return JSONResponse(content=health_status, status_code=status_code)
```

## CI/CD Pipeline

### GitHub Actions Workflow
```yaml
# .github/workflows/deploy.yml
name: Deploy NBA API

on:
  push:
    branches: [main]
  pull_request:
    branches: [main]

jobs:
  test:
    runs-on: ubuntu-latest
    
    services:
      postgres:
        image: postgres:15
        env:
          POSTGRES_PASSWORD: postgres
          POSTGRES_DB: test_nba_pbp
        options: >-
          --health-cmd pg_isready
          --health-interval 10s
          --health-timeout 5s
          --health-retries 5
    
    steps:
    - uses: actions/checkout@v3
    
    - name: Set up Python
      uses: actions/setup-python@v4
      with:
        python-version: '3.11'
    
    - name: Install dependencies
      run: |
        python -m pip install --upgrade pip
        pip install -r requirements.txt
        pip install pytest pytest-asyncio
    
    - name: Run tests
      run: |
        pytest src/api/test_api.py -v
      env:
        DATABASE_URL: postgresql://postgres:postgres@localhost:5432/test_nba_pbp
    
    - name: Run security scan
      uses: aquasecurity/trivy-action@master
      with:
        scan-type: 'fs'
        scan-ref: '.'
  
  build-and-deploy:
    needs: test
    runs-on: ubuntu-latest
    if: github.ref == 'refs/heads/main'
    
    steps:
    - uses: actions/checkout@v3
    
    - name: Build Docker image
      run: |
        docker build -t nba-api:${{ github.sha }} -f src/api/Dockerfile .
    
    - name: Deploy to Railway
      uses: railwayapp/railway-deploy@v1
      with:
        railway-token: ${{ secrets.RAILWAY_TOKEN }}
        service: nba-api
```

## Deployment Recommendations

### For Different Scales:

1. **MVP/Prototype**: Railway or Render
   - Pros: Zero ops, fast deployment
   - Suitable for: < 1000 requests/day

2. **Small Production**: Docker Compose on VPS
   - Pros: Cost-effective, full control
   - Suitable for: < 10,000 requests/day

3. **Medium Scale**: Google Cloud Run or AWS Fargate
   - Pros: Managed containers, auto-scaling
   - Suitable for: < 100,000 requests/day

4. **Large Scale**: Kubernetes (GKE, EKS, AKS)
   - Pros: Full orchestration, high availability
   - Suitable for: > 100,000 requests/day

### Cost Optimization:
- Use spot instances for non-critical workloads
- Implement auto-scaling based on metrics
- Use CDN for static content and caching
- Monitor and optimize database queries
- Implement request caching with Redis

### High Availability:
- Multi-region deployments
- Database replicas and failover
- Load balancing across multiple instances
- Circuit breakers for external dependencies
- Automated backup and disaster recovery

This deployment guide provides multiple options to suit different needs, from simple cloud deployments to enterprise-grade Kubernetes clusters.