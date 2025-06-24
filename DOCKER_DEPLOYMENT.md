# LLM Chatbot API - Docker Deployment Guide

This guide explains how to deploy the LLM Chatbot API using Docker. The Docker image is built without any environment variables and is configured entirely at runtime.

## 🔐 Security Model

- ✅ **No secrets in image** - All sensitive data provided at runtime
- ✅ **Environment validation** - Container checks for required variables on startup
- ✅ **Placeholder detection** - Prevents running with template placeholders
- ✅ **GitHub-safe** - Image can be safely pushed to public repositories

## Prerequisites

- Docker Engine 20.10+
- Docker Compose v2.0+ (recommended)
- External services: PostgreSQL, MinIO, Milvus, LLM API, Embeddings API

## Quick Start

### 1. Build or Pull the Docker Image

```bash
# Option A: Build locally
docker build -t llm-chatbot-api .

# Option B: Pull from registry (when available)
docker pull your-registry/llm-chatbot-api:latest
```

### 2. Configure Environment Variables

The image requires all configuration at runtime. Use one of these approaches:

#### Option A: Using docker-compose (Recommended)

```bash
# Copy the sample docker-compose file
cp docker-compose.sample.yml docker-compose.yml

# Edit docker-compose.yml and replace ALL placeholder values:
# - SECRET_KEY: Generate with: openssl rand -hex 32
# - All database passwords
# - Super admin credentials
# - External service URLs

# Optional: Validate configuration before deploying
./validate-env.sh

# Deploy
docker-compose up -d
```

#### Option B: Using .env file with docker-compose

```bash
# Copy the template
cp .env.template .env

# Edit .env and replace ALL __REQUIRED_*__ placeholders
# Then reference in docker-compose.yml:
# env_file:
#   - .env

docker-compose up -d
```

#### Option C: Direct docker run

```bash
docker run -d \
  --name llm-chatbot-api \
  -p 35430:35430 \
  -e SECRET_KEY="your_32_char_jwt_secret" \
  -e POSTGRES_HOST="your_postgres_host" \
  -e POSTGRES_USER="your_db_user" \
  -e POSTGRES_PASSWORD="your_db_password" \
  -e POSTGRES_DB="chatbot" \
  -e SUPER_ADMIN_USERNAME="admin" \
  -e SUPER_ADMIN_PASSWORD="secure_password" \
  -e SUPER_ADMIN_EMAIL="admin@company.com" \
  # ... add all other required variables
  llm-chatbot-api:latest
```

### 3. Environment Variables Configuration

**Security (REQUIRED for production):**

**Security (REQUIRED for production):**
```bash
SECRET_KEY=your_super_secure_jwt_secret_key_minimum_32_characters_long
POSTGRES_PASSWORD=your_secure_database_password
MINIO_SECRET_KEY=your_secure_minio_password
SUPER_ADMIN_PASSWORD=your_secure_admin_password
```

**Database Configuration:**
```bash
POSTGRES_USER=myuser
POSTGRES_PASSWORD=your_secure_database_password
POSTGRES_HOST=postgres  # or your database host
POSTGRES_PORT=5432
POSTGRES_DB=chatbot
```

**External Services (Configure based on your setup):**
```bash
OPENAI_API_BASE=http://your-llm-server:port/v1
LLM_MODEL=your-model-name
REMOTE_EMBEDDER_URL=http://your-embedder-server:port/embeddings
INFINITY_API_URL=http://your-infinity-server:port
MILVUS_URI=http://milvus:19530  # or your Milvus host
MINIO_ENDPOINT=minio:9000  # or your MinIO host
```

### 4. Application Startup Process

The Docker container automatically handles:
1. **Database Connection Wait** - Waits for PostgreSQL to be ready
2. **Alembic Migrations** - Runs `alembic upgrade head` automatically
3. **Super Admin Creation** - Initializes super admin from environment variables
4. **Service Start** - Starts the FastAPI application

### 5. Database Migration Management

For containers managed by docker-compose, use the provided helper script:

```bash
# Check current database version (requires ./alembic-docker.sh in docker-compose directory)
./alembic-docker.sh current

# For standalone containers, exec into the container:
docker exec -it llm-chatbot-api python -m alembic current
docker exec -it llm-chatbot-api python -m alembic history
docker exec -it llm-chatbot-api python -m alembic upgrade head
```

### 6. Super Admin Management

The super admin user is automatically created on first startup using environment variables. However, you may need to manage the super admin account later:

#### Reset Forgotten Super Admin Password

```bash
# Access the running container
docker-compose exec api bash

# Run the super admin management script
/app/reset-super-admin.sh

# Or directly reset password
python /app/app/scripts/recreate_super_admin.py --reset-password
```

#### Other Super Admin Operations

```bash
# Check current super admin info
docker-compose exec api /app/reset-super-admin.sh
# Choose option 4

# Recreate super admin completely
docker-compose exec api /app/reset-super-admin.sh
# Choose option 2

# Promote existing user to super admin
docker-compose exec api /app/reset-super-admin.sh
# Choose option 3
```

#### Alternative: Use the original script directly

```bash
# Interactive menu
docker-compose exec api /app/recreate_super_admin.sh

# Direct password reset
docker-compose exec api python /app/app/scripts/recreate_super_admin.py --reset-password

# Direct recreation with force
docker-compose exec api python /app/app/scripts/recreate_super_admin.py --force
```plains how to deploy the LLM Chatbot API using Docker and Docker Compose.

## Prerequisites

- Docker Engine 20.10+
- Docker Compose v2.0+
- At least 4GB RAM available for the containers
- 10GB+ disk space for databases and file storage

## Quick Start

### 1. Clone and Prepare

```bash
# Navigate to your project directory
cd /path/to/your/project

# Copy environment template
cp .env.docker .env

# Edit the environment file with your settings
nano .env
```

### 2. Configure Environment Variables

Edit the `.env` file and update these critical settings:

**Security (REQUIRED for production):**
```bash
SECRET_KEY=your_super_secure_jwt_secret_key_minimum_32_characters_long
POSTGRES_PASSWORD=your_secure_database_password
MINIO_SECRET_KEY=your_secure_minio_password
SUPER_ADMIN_PASSWORD=your_secure_admin_password
```

**External Services (Configure based on your setup):**
```bash
OPENAI_API_BASE=http://your-llm-server:port/v1
LLM_MODEL=your-model-name
REMOTE_EMBEDDER_URL=http://your-embedder-server:port/embeddings
INFINITY_API_URL=http://your-infinity-server:port
```

### 3. Build and Deploy

```bash
# Build and start all services
docker-compose up -d

# Check logs
docker-compose logs -f

# Check service status
docker-compose ps
```

### 7. Access the Application

- **API Health Check**: http://localhost:35430/health
- **MinIO Console**: Configure according to your setup
- **PostgreSQL**: Configure according to your setup

## Docker Image Features

### Built-in Scripts
- `/app/docker-entrypoint.sh` - Main entrypoint with database wait and migration
- `/app/reset-super-admin.sh` - Docker-optimized super admin management
- `/app/recreate_super_admin.sh` - Original super admin management script
- `/app/alembic-docker.sh` - Alembic management (for docker-compose setups)

### Health Checks
The Dockerfile includes health checks that monitor:
- API availability on port 35430
- Service responsiveness

### Security Features
- Non-root user (`appuser`)
- Minimal system dependencies
- Environment-based configuration
- Secure password handling

## Sample docker-compose.yml

Since docker-compose files are managed separately, here's a basic template:

```yaml
version: '3.8'
services:
  api:
    image: llm-chatbot-api:latest
    container_name: llm-chatbot-api
    ports:
      - "35430:35430"
    environment:
      # Database
      - POSTGRES_HOST=postgres
      - POSTGRES_USER=myuser
      - POSTGRES_PASSWORD=secure_password
      - POSTGRES_DB=chatbot
      # Security
      - SECRET_KEY=your_jwt_secret_32_chars_min
      - SUPER_ADMIN_PASSWORD=secure_admin_password
      # External services
      - OPENAI_API_BASE=http://your-llm-server/v1
      - MILVUS_URI=http://milvus:19530
      - MINIO_ENDPOINT=minio:9000
    depends_on:
      - postgres
      - minio
      - milvus
    restart: unless-stopped
    volumes:
      - ./logs:/app/logs

  postgres:
    image: postgres:15-alpine
    environment:
      - POSTGRES_USER=myuser
      - POSTGRES_PASSWORD=secure_password
      - POSTGRES_DB=chatbot
    volumes:
      - postgres_data:/var/lib/postgresql/data
    ports:
      - "5432:5432"

  # Add MinIO, Milvus, etc. as needed

volumes:
  postgres_data:
```

## Production Deployment

### 1. Security Hardening

```bash
# Generate a secure JWT secret
openssl rand -hex 32

# Use strong passwords for all services
# Restrict network access using firewall rules
# Enable HTTPS with reverse proxy (nginx/traefik)
```

### 2. Reverse Proxy Setup (Nginx example)

```nginx
server {
    listen 80;
    server_name your-domain.com;
    
    location / {
        proxy_pass http://localhost:35430;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
}
```

### 3. SSL/HTTPS Setup

Use Let's Encrypt with certbot or your preferred SSL provider.

### 4. Monitoring and Logs

```bash
# View real-time logs
docker-compose logs -f api

# Monitor resource usage
docker stats

# Backup databases
docker-compose exec postgres pg_dump -U myuser chatbot > backup.sql
```

## Scaling and Performance

### 1. Database Optimization

```yaml
# In docker-compose.yml, add to postgres service:
environment:
  - POSTGRES_SHARED_PRELOAD_LIBRARIES=pg_stat_statements
  - POSTGRES_MAX_CONNECTIONS=200
```

### 2. API Scaling

```yaml
# Scale API service
deploy:
  replicas: 3
```

### 3. Resource Limits

```yaml
# Add to each service:
deploy:
  resources:
    limits:
      memory: 1G
      cpus: '0.5'
```

## Troubleshooting

### Common Issues

1. **Database Connection Failed**
   ```bash
   # Check container logs
   docker logs llm-chatbot-api
   
   # Verify database credentials in environment
   docker exec -it llm-chatbot-api env | grep POSTGRES
   ```

2. **Container Won't Start**
   ```bash
   # Check container status
   docker ps -a
   
   # View container logs
   docker logs llm-chatbot-api
   
   # Check if required services are running
   docker ps | grep -E "(postgres|minio|milvus)"
   ```

3. **Alembic Migration Issues**
   ```bash
   # Check current migration status
   docker exec -it llm-chatbot-api python -m alembic current
   
   # View migration history
   docker exec -it llm-chatbot-api python -m alembic history
   
   # If migrations are out of sync, stamp the database
   ./alembic-docker.sh stamp head
   ```

4. **API Won't Start**
   ```bash
   # Check API logs
   docker-compose logs api
   
   # Verify all environment variables are set
   docker-compose exec api env | grep -E "(POSTGRES|MINIO|MILVUS)"
   ```

### Health Checks

```bash
# API health
curl http://localhost:35430/health

# Check container health status
docker ps --filter name=llm-chatbot-api

# Database health (if using separate postgres container)
docker exec -it postgres-container pg_isready -U myuser

# Container resource usage
docker stats llm-chatbot-api
```

## Backup and Recovery

### Database Backup
```bash
# Create backup (adjust container names as needed)
docker exec -it postgres-container pg_dump -U myuser chatbot > backup_$(date +%Y%m%d).sql

# Or backup from API container
docker exec -it llm-chatbot-api pg_dump postgresql://user:pass@host:port/db > backup.sql

# Restore backup
docker-compose exec -T postgres psql -U myuser chatbot < backup_20231201.sql
```

### Volume Backup
```bash
# Backup all volumes
docker run --rm -v llm-chatbot-api_postgres_data:/data -v $(pwd):/backup alpine tar czf /backup/postgres_backup.tar.gz -C /data .
```

## Environment Variables Reference

See `.env.docker` for a complete list of configurable environment variables.

### Required Variables
- `SECRET_KEY`: JWT signing key (32+ characters)
- `POSTGRES_PASSWORD`: Database password
- `MINIO_SECRET_KEY`: Object storage password
- `SUPER_ADMIN_PASSWORD`: Initial admin user password

### Optional Variables
- `LLM_*`: Language model configuration
- `MILVUS_*`: Vector database settings
- `MINIO_*`: Object storage settings

## Updates and Maintenance

```bash
# Update to latest images
docker-compose pull

# Rebuild and restart
docker-compose up -d --build

# Clean up old images
docker image prune -f
```
