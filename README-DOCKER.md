# LLM Chatbot API - Docker Image

A production-ready Docker image for the LLM Chatbot API. The image contains no secrets and is fully configured at runtime via environment variables.

## 🚀 Quick Build

```bash
# Build the image
docker build -t llm-chatbot-api .

# Push to your registry
docker tag llm-chatbot-api your-registry/llm-chatbot-api:latest
docker push your-registry/llm-chatbot-api:latest
```

## 🔐 Security Features

- ✅ **Zero secrets in image** - All configuration via runtime environment
- ✅ **Environment validation** - Startup checks for required variables
- ✅ **Placeholder detection** - Prevents running with template values
- ✅ **GitHub-safe** - Image can be pushed to public repositories

## � Required Environment Variables

### Critical (Must be set)
```bash
# Security
SECRET_KEY=your_32_character_jwt_secret
SUPER_ADMIN_USERNAME=admin
SUPER_ADMIN_PASSWORD=secure_password
SUPER_ADMIN_EMAIL=admin@company.com

# Database
POSTGRES_HOST=your_postgres_host
POSTGRES_USER=your_db_user  
POSTGRES_PASSWORD=your_db_password
POSTGRES_DB=chatbot
```

### Application Settings
```bash
# LLM Configuration
OPENAI_API_BASE=http://your-llm-server/v1
LLM_MODEL=your-model-name
LLM_TEMPERATURE=0.1
LLM_MAX_TOKENS=2000

# RAG/Vector Database
MILVUS_URI=http://your-milvus:19530
DEFAULT_COLLECTION=default_collection
RETRIEVER_TOP_K=10

# Object Storage
MINIO_ENDPOINT=your-minio:9000
MINIO_ACCESS_KEY=minioadmin
MINIO_SECRET_KEY=secure_minio_password

# Embeddings
REMOTE_EMBEDDER_URL=http://your-embedder/embeddings
```

## 🐳 What the Image Contains

- ✅ FastAPI application with all dependencies
- ✅ Automatic database migration (Alembic)
- ✅ Super admin management scripts
- ✅ Health checks and monitoring
- ✅ Non-root user security
- ✅ Environment validation

## 🔧 Runtime Behavior

When the container starts, it automatically:

1. **Validates** all required environment variables
2. **Waits** for database to be ready
3. **Runs** Alembic migrations (`alembic upgrade head`)
4. **Creates** super admin user from environment variables
5. **Initializes** default configurations from environment
6. **Starts** the FastAPI application

## 🛠️ Management Scripts

Available inside the running container:

```bash
# Reset super admin password
docker exec -it container-name /app/reset-super-admin.sh

# Check super admin info
docker exec -it container-name /app/reset-super-admin.sh
# Choose option 4

# Manual database operations
docker exec -it container-name python -m alembic current
docker exec -it container-name python -m alembic history
```

## 📖 Complete Reference

See `.env.template` for all available environment variables and `docker-compose.sample.yml` for a complete deployment example.

## 🛠️ Built-in Scripts

- **Super Admin Management**: `/app/reset-super-admin.sh`
- **Database Migrations**: Automatic via Alembic
- **Health Monitoring**: Built-in health checks

## 📚 Documentation

See `DOCKER_DEPLOYMENT.md` for comprehensive deployment guide.

## 🔐 Super Admin Reset

If you forget the super admin password:

```bash
docker exec -it llm-chatbot-api /app/reset-super-admin.sh
```

## 🏗️ Architecture

```
┌─────────────────┐    ┌──────────────┐    ┌─────────────┐
│   FastAPI App   │───▶│ PostgreSQL   │    │   MinIO     │
│  (Port 35430)   │    │  Database    │    │  Storage    │
└─────────────────┘    └──────────────┘    └─────────────┘
        │
        ▼
┌─────────────────┐    ┌──────────────┐    ┌─────────────┐
│     Milvus      │    │ LLM Service  │    │ Embeddings  │
│ Vector Database │    │ (External)   │    │  Service    │
└─────────────────┘    └──────────────┘    └─────────────┘
```

## 🔄 Updates

```bash
# Rebuild with latest changes
docker build -t llm-chatbot-api:latest .

# Update running container
docker stop llm-chatbot-api
docker rm llm-chatbot-api
docker run -d --name llm-chatbot-api ... # with your parameters
```
