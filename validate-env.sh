#!/bin/bash
# Environment validation script for docker-compose deployment
# Run this before deploying to catch configuration issues early

set -e

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

print_header() {
    echo -e "${BLUE}======================================${NC}"
    echo -e "${BLUE} LLM Chatbot API - Environment Check ${NC}"
    echo -e "${BLUE}======================================${NC}"
    echo ""
}

print_success() {
    echo -e "${GREEN}✅ $1${NC}"
}

print_warning() {
    echo -e "${YELLOW}⚠️  $1${NC}"
}

print_error() {
    echo -e "${RED}❌ $1${NC}"
}

print_info() {
    echo -e "${BLUE}ℹ️  $1${NC}"
}

# Track issues
ERRORS=0
WARNINGS=0

check_file_exists() {
    local file=$1
    local description=$2
    
    if [[ -f "$file" ]]; then
        print_success "$description found: $file"
        return 0
    else
        print_error "$description not found: $file"
        ((ERRORS++))
        return 1
    fi
}

check_env_var() {
    local var_name=$1
    local var_value=$2
    local is_secret=${3:-false}
    
    if [[ -z "$var_value" ]]; then
        print_error "Missing required variable: $var_name"
        ((ERRORS++))
        return 1
    elif [[ "$var_value" == *"__REQUIRED"* ]]; then
        print_error "Placeholder not replaced: $var_name"
        ((ERRORS++))
        return 1
    elif [[ "$var_value" == *"your_"* ]] || [[ "$var_value" == *"changeme"* ]]; then
        print_warning "Possible placeholder value: $var_name"
        ((WARNINGS++))
        return 1
    else
        if [[ "$is_secret" == "true" ]]; then
            print_success "$var_name: [REDACTED]"
        else
            print_success "$var_name: $var_value"
        fi
        return 0
    fi
}

check_docker_compose() {
    print_info "Checking docker-compose.yml configuration..."
    
    if [[ ! -f "docker-compose.yml" ]]; then
        print_error "docker-compose.yml not found"
        print_info "Copy docker-compose.sample.yml to docker-compose.yml and configure it"
        ((ERRORS++))
        return 1
    fi
    
    # Check if it looks like the sample file (contains placeholders)
    if grep -q "__REQUIRED" docker-compose.yml 2>/dev/null; then
        print_error "docker-compose.yml contains unresolved placeholders"
        print_info "Replace all __REQUIRED_*__ values with actual configuration"
        ((ERRORS++))
    elif grep -q "change_this" docker-compose.yml 2>/dev/null; then
        print_warning "docker-compose.yml may contain placeholder passwords"
        ((WARNINGS++))
    else
        print_success "docker-compose.yml appears to be configured"
    fi
}

check_env_file() {
    if [[ -f ".env" ]]; then
        print_info "Found .env file, checking variables..."
        
        # Source the .env file
        set -a
        source .env
        set +a
        
        # Check critical variables
        check_env_var "SECRET_KEY" "$SECRET_KEY" true
        check_env_var "POSTGRES_HOST" "$POSTGRES_HOST"
        check_env_var "POSTGRES_USER" "$POSTGRES_USER"
        check_env_var "POSTGRES_PASSWORD" "$POSTGRES_PASSWORD" true
        check_env_var "POSTGRES_DB" "$POSTGRES_DB"
        check_env_var "SUPER_ADMIN_USERNAME" "$SUPER_ADMIN_USERNAME"
        check_env_var "SUPER_ADMIN_PASSWORD" "$SUPER_ADMIN_PASSWORD" true
        check_env_var "SUPER_ADMIN_EMAIL" "$SUPER_ADMIN_EMAIL"
        
        # Check JWT secret length
        if [[ -n "$SECRET_KEY" && ${#SECRET_KEY} -lt 32 ]]; then
            print_warning "SECRET_KEY should be at least 32 characters long"
            ((WARNINGS++))
        fi
        
    else
        print_info "No .env file found (environment variables in docker-compose.yml)"
    fi
}

check_docker() {
    print_info "Checking Docker setup..."
    
    if ! command -v docker &> /dev/null; then
        print_error "Docker not found in PATH"
        ((ERRORS++))
    else
        print_success "Docker found: $(docker --version)"
    fi
    
    if ! command -v docker-compose &> /dev/null; then
        if ! docker compose version &> /dev/null; then
            print_error "docker-compose not found"
            ((ERRORS++))
        else
            print_success "Docker Compose found: $(docker compose version)"
        fi
    else
        print_success "Docker Compose found: $(docker-compose --version)"
    fi
}

generate_jwt_secret() {
    print_info "Need a JWT secret? Generate one with:"
    echo "  openssl rand -hex 32"
    echo ""
}

main() {
    print_header
    
    check_docker
    echo ""
    
    check_docker_compose
    echo ""
    
    check_env_file
    echo ""
    
    # Summary
    echo -e "${BLUE}======================================${NC}"
    echo -e "${BLUE}         VALIDATION SUMMARY           ${NC}"
    echo -e "${BLUE}======================================${NC}"
    
    if [[ $ERRORS -eq 0 && $WARNINGS -eq 0 ]]; then
        print_success "Configuration looks good! Ready to deploy."
        echo ""
        print_info "Deploy with: docker-compose up -d"
    elif [[ $ERRORS -eq 0 ]]; then
        print_warning "Configuration has $WARNINGS warning(s) but should work"
        echo ""
        print_info "Deploy with: docker-compose up -d"
    else
        print_error "Configuration has $ERRORS error(s) and $WARNINGS warning(s)"
        echo ""
        print_info "Fix the errors above before deploying"
        
        if [[ $ERRORS -gt 0 ]]; then
            echo ""
            generate_jwt_secret
        fi
        
        exit 1
    fi
}

main "$@"
