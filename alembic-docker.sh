#!/bin/bash
# Alembic management script for Docker environment

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Function to print colored output
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

# Check if docker-compose is available
if ! command -v docker-compose &> /dev/null; then
    print_error "docker-compose is not installed or not in PATH"
    exit 1
fi

# Function to run alembic commands in container
run_alembic() {
    print_status "Running: alembic $*"
    docker-compose exec api python -m alembic "$@"
}

# Function to check if containers are running
check_containers() {
    if ! docker-compose ps | grep -q "api.*Up"; then
        print_error "API container is not running. Start it first with: docker-compose up -d"
        exit 1
    fi
}

# Main script logic
case "${1:-help}" in
    "current")
        print_status "Checking current database revision..."
        check_containers
        run_alembic current
        ;;
    
    "history")
        print_status "Showing migration history..."
        check_containers
        run_alembic history
        ;;
    
    "upgrade")
        print_status "Upgrading database to latest revision..."
        check_containers
        run_alembic upgrade head
        print_success "Database upgraded successfully!"
        ;;
    
    "downgrade")
        if [ -z "$2" ]; then
            print_error "Please specify the target revision: $0 downgrade <revision>"
            exit 1
        fi
        print_warning "Downgrading database to revision: $2"
        print_warning "This operation may cause data loss!"
        read -p "Are you sure? (y/N): " confirm
        if [[ $confirm == [yY] ]]; then
            check_containers
            run_alembic downgrade "$2"
            print_success "Database downgraded to revision: $2"
        else
            print_status "Operation cancelled."
        fi
        ;;
    
    "revision")
        if [ -z "$2" ]; then
            print_error "Please specify a migration message: $0 revision 'your message here'"
            exit 1
        fi
        print_status "Creating new migration: $2"
        check_containers
        run_alembic revision --autogenerate -m "$2"
        print_success "New migration created!"
        ;;
    
    "stamp")
        if [ -z "$2" ]; then
            print_error "Please specify the revision: $0 stamp <revision>"
            exit 1
        fi
        print_status "Stamping database with revision: $2"
        check_containers
        run_alembic stamp "$2"
        print_success "Database stamped with revision: $2"
        ;;
    
    "heads")
        print_status "Showing current heads..."
        check_containers
        run_alembic heads
        ;;
    
    "show")
        if [ -z "$2" ]; then
            print_error "Please specify the revision: $0 show <revision>"
            exit 1
        fi
        print_status "Showing migration details for: $2"
        check_containers
        run_alembic show "$2"
        ;;
    
    "help"|"--help"|"-h")
        echo "Alembic Management Script for Docker"
        echo "===================================="
        echo ""
        echo "Usage: $0 <command> [arguments]"
        echo ""
        echo "Commands:"
        echo "  current               Show current database revision"
        echo "  history               Show migration history"
        echo "  upgrade               Upgrade database to latest revision"
        echo "  downgrade <revision>  Downgrade database to specific revision"
        echo "  revision '<message>'  Create new migration with autogenerate"
        echo "  stamp <revision>      Stamp database with specific revision"
        echo "  heads                 Show current heads"
        echo "  show <revision>       Show details of specific migration"
        echo "  help                  Show this help message"
        echo ""
        echo "Examples:"
        echo "  $0 current"
        echo "  $0 upgrade"
        echo "  $0 revision 'Add user profile table'"
        echo "  $0 downgrade -1"
        echo "  $0 stamp head"
        echo ""
        echo "Note: Containers must be running before using this script."
        echo "Start them with: docker-compose up -d"
        ;;
    
    *)
        print_error "Unknown command: $1"
        print_status "Use '$0 help' to see available commands"
        exit 1
        ;;
esac
