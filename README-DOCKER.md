# LLM Chatbot API - Docker Image

A secure, production-ready Docker image for the LLM Chatbot API. The image contains no secrets and is configured entirely at runtime.

## 🔐 Security Features

- ✅ **Zero secrets in image** - All configuration via runtime environment
- ✅ **Environment validation** - Startup checks for required variables
- ✅ **Placeholder detection** - Prevents running with template values
- ✅ **GitHub-safe** - Image can be pushed to public repositories

## 🚀 Quick Start

```bash
# 1. Build or pull the image
docker build -t llm-chatbot-api .

# 2. Use the sample docker-compose
cp docker-compose.sample.yml docker-compose.yml
# Edit and replace ALL placeholder values

# 3. Deploy
docker-compose up -d
```

## ⚠️ CRITICAL: Replace ALL Placeholders

The `.env.template` contains placeholders like `__REQUIRED_*__`. You MUST replace ALL of these:

```bash
# ❌ WRONG - Don't use template values
SECRET_KEY=__REQUIRED_JWT_SECRET_MINIMUM_32_CHARS__

# ✅ CORRECT - Use real values  
SECRET_KEY=a1b2c3d4e5f6789012345678901234567890abcdef
```

## 🔧 Required Environment Variables

### Security (Critical)
```bash
SECRET_KEY=your_32_character_jwt_secret
SUPER_ADMIN_USERNAME=your_admin_username
SUPER_ADMIN_PASSWORD=your_secure_password
SUPER_ADMIN_EMAIL=admin@yourcompany.com
```

### Database (Critical)
```bash
POSTGRES_HOST=your_postgres_host
POSTGRES_USER=your_db_user  
POSTGRES_PASSWORD=your_db_password
POSTGRES_DB=chatbot
```

### External Services
```bash
OPENAI_API_BASE=http://your-llm-server/v1
MILVUS_URI=http://your-milvus:19530
MINIO_ENDPOINT=your-minio:9000
REMOTE_EMBEDDER_URL=http://your-embedder/embeddings
```

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
