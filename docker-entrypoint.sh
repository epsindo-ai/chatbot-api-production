#!/bin/bash
set -e

echo "🚀 Starting LLM Chatbot API..."

# Set cache directory for Docling models to avoid permission issues
export XDG_CACHE_HOME=/app/.cache

# Function to check required environment variables
check_required_env() {
    local missing_vars=()
    
    # Check critical environment variables
    [ -z "$SECRET_KEY" ] && missing_vars+=("SECRET_KEY")
    [ -z "$POSTGRES_HOST" ] && missing_vars+=("POSTGRES_HOST")
    [ -z "$POSTGRES_USER" ] && missing_vars+=("POSTGRES_USER")
    [ -z "$POSTGRES_PASSWORD" ] && missing_vars+=("POSTGRES_PASSWORD")
    [ -z "$POSTGRES_DB" ] && missing_vars+=("POSTGRES_DB")
    [ -z "$SUPER_ADMIN_USERNAME" ] && missing_vars+=("SUPER_ADMIN_USERNAME")
    [ -z "$SUPER_ADMIN_PASSWORD" ] && missing_vars+=("SUPER_ADMIN_PASSWORD")
    [ -z "$SUPER_ADMIN_EMAIL" ] && missing_vars+=("SUPER_ADMIN_EMAIL")
    
    # Check for placeholder values that weren't replaced
    if [[ "$SECRET_KEY" == *"__REQUIRED"* ]]; then
        missing_vars+=("SECRET_KEY (placeholder not replaced)")
    fi
    if [[ "$POSTGRES_PASSWORD" == *"__REQUIRED"* ]]; then
        missing_vars+=("POSTGRES_PASSWORD (placeholder not replaced)")
    fi
    if [[ "$SUPER_ADMIN_PASSWORD" == *"__REQUIRED"* ]]; then
        missing_vars+=("SUPER_ADMIN_PASSWORD (placeholder not replaced)")
    fi
    
    if [ ${#missing_vars[@]} -ne 0 ]; then
        echo "❌ ERROR: Missing or invalid required environment variables:"
        printf '   - %s\n' "${missing_vars[@]}"
        echo ""
        echo "💡 Please ensure all required environment variables are set in your docker-compose.yml"
        echo "   Refer to .env.template for the complete list of required variables."
        echo ""
        exit 1
    fi
}

# Check environment variables
echo "🔍 Checking environment variables..."
check_required_env
echo "✅ Environment variables validated!"

# Ensure Docling models are available
echo "🤖 Checking Docling models..."
# Check both possible locations where models might be
if [ -d "/app/.cache/docling/models" ] && [ -n "$(ls -A /app/.cache/docling/models 2>/dev/null)" ]; then
    echo "✅ Docling models found in /app/.cache/docling/models"
elif [ -d "/root/.cache/docling/models" ] && [ -n "$(ls -A /root/.cache/docling/models 2>/dev/null)" ]; then
    echo "✅ Docling models found in /root/.cache/docling/models"
else
    echo "⚠️  Docling models not found in expected locations"
    echo "📥 Downloading models as fallback..."
    if docling-tools models download; then
        echo "✅ Docling models downloaded successfully"
    else
        echo "❌ Failed to download models. Document processing may fail."
    fi
fi

# Wait for database to be ready
echo "⏳ Waiting for database to be ready..."
while ! nc -z ${POSTGRES_HOST:-postgres} ${POSTGRES_PORT:-5432}; do
  echo "Waiting for PostgreSQL at ${POSTGRES_HOST:-postgres}:${POSTGRES_PORT:-5432}..."
  sleep 2
done
echo "✅ Database is ready!"

# Run Alembic migrations
echo "🔄 Running database migrations..."
python -m alembic upgrade head

if [ $? -eq 0 ]; then
    echo "✅ Database migrations completed successfully!"
else
    echo "❌ Database migrations failed!"
    exit 1
fi

# Start the application
echo "🎯 Starting FastAPI application..."
exec python -m uvicorn app.main:app --host 0.0.0.0 --port 35430 --workers 1
