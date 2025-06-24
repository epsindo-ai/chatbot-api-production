#!/bin/bash
set -e

echo "🚀 Starting LLM Chatbot API..."

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
