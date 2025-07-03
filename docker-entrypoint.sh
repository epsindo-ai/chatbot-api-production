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

# Setup Docling models
echo "🤖 Setting up Docling models..."
echo "Cache directory: $XDG_CACHE_HOME"
echo "Models directory: $XDG_CACHE_HOME/docling/models"

# Create cache directory if it doesn't exist
mkdir -p "$XDG_CACHE_HOME/docling/models"

# Check if models exist in permanent location
if [ -d "/opt/docling-models/docling/models" ] && [ "$(find /opt/docling-models/docling/models -type f 2>/dev/null | wc -l)" -gt 0 ]; then
    echo "📥 Copying models from permanent location..."
    # Use rsync-style copying to preserve directory structure
    (cd /opt/docling-models/docling/models && find . -type d -exec mkdir -p "$XDG_CACHE_HOME/docling/models/{}" \;)
    (cd /opt/docling-models/docling/models && find . -type f -exec cp {} "$XDG_CACHE_HOME/docling/models/{}" \;)
    echo "✅ Models copy completed"
    echo "Total files in cache: $(find $XDG_CACHE_HOME/docling/models -type f 2>/dev/null | wc -l)"
    
    # Verify specific EasyOcr model exists
    if [ -f "$XDG_CACHE_HOME/docling/models/EasyOcr/craft_mlt_25k.pth" ]; then
        echo "✅ EasyOcr craft_mlt_25k.pth model found"
    else
        echo "⚠️ Warning: EasyOcr craft_mlt_25k.pth model not found in expected location"
        echo "Available files in EasyOcr directory:"
        ls -la "$XDG_CACHE_HOME/docling/models/EasyOcr/" 2>/dev/null || echo "EasyOcr directory not found"
        echo "Directory structure:"
        find "$XDG_CACHE_HOME/docling/models" -type d | head -10
    fi
else
    echo "📥 Downloading models (not found in permanent location)..."
    if docling-tools models download; then
        echo "✅ Models downloaded successfully"
    else
        echo "❌ Failed to download models - continuing with potential on-demand download"
    fi
fi

# Verify models are available
if [ -d "$XDG_CACHE_HOME/docling/models" ] && [ "$(find $XDG_CACHE_HOME/docling/models -type f 2>/dev/null | wc -l)" -gt 0 ]; then
    echo "✅ Docling models are ready ($(find $XDG_CACHE_HOME/docling/models -type f | wc -l) files)"
    echo "Sample model files:"
    find $XDG_CACHE_HOME/docling/models -name "*.pth" -o -name "*.bin" -o -name "*.safetensors" | head -3
else
    echo "⚠️ Warning: No models found in cache directory"
    echo "Models will be downloaded on first document processing"
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
exec python -m uvicorn app.main:app --host 0.0.0.0 --port 35430 --workers 5
