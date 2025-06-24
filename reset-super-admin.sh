#!/bin/bash
# Docker Super Admin Management Script
# Usage: docker-compose exec api /app/reset-super-admin.sh

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

print_status() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

print_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

print_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

echo "🔧 Docker Super Admin Management Tool"
echo "======================================"
echo ""
echo "Choose an option:"
echo "1. Reset super admin password"
echo "2. Recreate super admin (full replacement)"
echo "3. Promote existing user to super admin"
echo "4. Check current super admin info"
echo "5. Force recreate (no confirmations)"
echo "6. Exit"
echo ""

read -p "Enter your choice (1-6): " choice

case $choice in
    1)
        print_status "Starting password reset..."
        python /app/app/scripts/recreate_super_admin.py --reset-password
        ;;
    2)
        print_status "Starting super admin recreation..."
        python /app/app/scripts/recreate_super_admin.py
        ;;
    3)
        print_status "Starting user promotion..."
        python /app/app/scripts/recreate_super_admin.py --promote
        ;;
    4)
        print_status "Checking super admin info..."
        python -c "
import sys
import os
sys.path.insert(0, '/app')
from sqlalchemy.orm import Session
from app.db.database import engine
from app.db import models
from app.db.models import UserRole

db = Session(engine)
try:
    super_admin = db.query(models.User).filter(models.User.role == UserRole.SUPER_ADMIN).first()
    if super_admin:
        print(f'📋 Current Super Admin:')
        print(f'   Username: {super_admin.username}')
        print(f'   Email: {super_admin.email}')
        print(f'   Active: {super_admin.is_active}')
        print(f'   Created: {super_admin.created_at}')
        print(f'   Last Updated: {super_admin.updated_at}')
    else:
        print('❌ No super admin found in database')
except Exception as e:
    print(f'Error: {e}')
finally:
    db.close()
"
        ;;
    5)
        print_warning "⚠️  WARNING: Force mode will skip all confirmations!"
        read -p "Are you sure? Type 'YES' to continue: " confirm
        if [ "$confirm" = "YES" ]; then
            python /app/app/scripts/recreate_super_admin.py --force
        else
            print_status "Operation cancelled."
        fi
        ;;
    6)
        print_status "Goodbye!"
        exit 0
        ;;
    *)
        print_error "Invalid choice. Please run the script again."
        exit 1
        ;;
esac

print_success "Operation completed!"
