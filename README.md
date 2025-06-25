# LLM Chatbot API - Docker

Production-ready Docker image for the LLM Chatbot API. Zero secrets in the image, fully configured at runtime.

## 🚀 Quick Start

```bash
# 1. Build the image
docker build -t llm-chatbot-api .

# 2. Create your docker-compose.yml (see example below)

# 3. Deploy
docker-compose up -d
```

## 📋 What You Need

- **Database**: PostgreSQL
- **Vector DB**: Milvus  
- **Storage**: MinIO
- **LLM API**: OpenAI-compatible endpoint
- **Embeddings**: Text embedding service

## 🔧 Environment Configuration

All configuration is done via environment variables in your `docker-compose.yml`:

### Essential Variables
```yaml
environment:
  # Security (generate with: openssl rand -hex 32)
  - SECRET_KEY=your_32_character_jwt_secret
  
  # Admin Account  
  - SUPER_ADMIN_USERNAME=admin
  - SUPER_ADMIN_PASSWORD=secure_password
  - SUPER_ADMIN_EMAIL=admin@company.com
  
  # Database
  - POSTGRES_HOST=postgres
  - POSTGRES_USER=chatbot
  - POSTGRES_PASSWORD=db_password
  - POSTGRES_DB=chatbot
  
  # LLM Service
  - OPENAI_API_BASE=http://your-llm-server/v1
  - LLM_MODEL=your-model-name
  
  # Vector Database
  - MILVUS_URI=http://milvus:19530
  
  # Object Storage
  - MINIO_ENDPOINT=minio:9000
  - MINIO_ACCESS_KEY=minioadmin
  - MINIO_SECRET_KEY=minio_password
```

## 🐳 Complete Example

Minimal `docker-compose.yml`:

```yaml
version: '3.8'
services:
  api:
    image: your-registry/llm-chatbot-api:latest
    ports:
      - "35430:35430"
    environment:
      - SECRET_KEY=a1b2c3d4e5f6789012345678901234567890abcd
      - SUPER_ADMIN_USERNAME=admin
      - SUPER_ADMIN_PASSWORD=MySecurePassword123
      - SUPER_ADMIN_EMAIL=admin@company.com
      - POSTGRES_HOST=postgres
      - POSTGRES_USER=chatbot
      - POSTGRES_PASSWORD=DbPassword123
      - POSTGRES_DB=chatbot
      - OPENAI_API_BASE=http://ollama:11434/v1
      - LLM_MODEL=llama2-7b-chat
      - MILVUS_URI=http://milvus:19530
      - MINIO_ENDPOINT=minio:9000
      - MINIO_ACCESS_KEY=minioadmin
      - MINIO_SECRET_KEY=MinioPassword123
      - REMOTE_EMBEDDER_URL=http://embeddings:8080/embeddings
    depends_on:
      - postgres
      - milvus
      - minio

  postgres:
    image: postgres:15-alpine
    environment:
      - POSTGRES_USER=chatbot
      - POSTGRES_PASSWORD=DbPassword123
      - POSTGRES_DB=chatbot
    volumes:
      - postgres_data:/var/lib/postgresql/data

  milvus:
    image: milvusdb/milvus:latest
    command: ["milvus", "run", "standalone"]
    volumes:
      - milvus_data:/var/lib/milvus
    ports:
      - "19530:19530"

  minio:
    image: minio/minio:latest
    command: server /data --console-address ":9001"
    environment:
      - MINIO_ROOT_USER=minioadmin
      - MINIO_ROOT_PASSWORD=MinioPassword123
    volumes:
      - minio_data:/data
    ports:
      - "9000:9000"
      - "9001:9001"

volumes:
  postgres_data:
  milvus_data:
  minio_data:
```

## ✅ What Happens Automatically

When the container starts:

1. **Validates** all required environment variables
2. **Ensures** Docling models are downloaded (for document processing)
3. **Waits** for database to be ready
4. **Runs** database migrations (Alembic)
5. **Creates** super admin user from environment
6. **Initializes** configurations from environment
7. **Starts** the FastAPI application

## 🛠️ Management

```bash
# Check health
curl http://localhost:35430/health

# Reset super admin password
docker exec -it container-name /app/reset-super-admin.sh

# View API docs
open http://localhost:35430/docs
```

## 📚 Repository Contents

**Core Files:**
- `Dockerfile` - Production-ready image definition
- `docker-entrypoint.sh` - Automatic startup script
- `requirements.txt` - Python dependencies
- `app/` - FastAPI application code

**Configuration:**
- `.env.template` - All environment variables reference
- `docker-compose.sample.yml` - Complete deployment example

**Management:**
- `reset-super-admin.sh` - Container super admin management
- `recreate_super_admin.sh` - Legacy admin management script

**Documentation:**
- `DOCKER_DEPLOYMENT.md` - Detailed deployment guide

## 🔐 Security

- ✅ No secrets in Docker image
- ✅ Runtime environment validation
- ✅ GitHub-safe for public repositories
