#!/bin/bash

# =============================================================================
# Digital Ocean Deployment Script
# PowerPoint Slide Creator - ekona
# =============================================================================

set -e  # Exit on any error

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Print colored output
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

# Check if doctl is installed
check_doctl() {
    if ! command -v doctl &> /dev/null; then
        print_error "doctl (Digital Ocean CLI) is not installed"
        print_status "Install it with: brew install doctl (macOS) or snap install doctl (Linux)"
        print_status "Then authenticate: doctl auth init"
        exit 1
    fi
    
    print_success "doctl is installed"
}

# Check if user is authenticated
check_auth() {
    if ! doctl account get &> /dev/null; then
        print_error "You are not authenticated with Digital Ocean"
        print_status "Run: doctl auth init"
        exit 1
    fi
    
    print_success "Digital Ocean authentication verified"
}

# Check if required environment file exists
check_env() {
    if [ ! -f ".env.production" ]; then
        print_error ".env.production file not found"
        print_status "Copy .env.production.template to .env.production and configure it"
        exit 1
    fi
    
    print_success "Production environment file found"
}

# Validate environment variables
validate_env() {
    print_status "Validating environment variables..."
    
    source .env.production
    
    local required_vars=(
        "NEXT_PUBLIC_SUPABASE_URL"
        "NEXT_PUBLIC_SUPABASE_ANON_KEY" 
        "SUPABASE_SERVICE_ROLE_KEY"
        "OPENAI_API_KEY"
        "NEXTAUTH_SECRET"
        "JWT_SECRET"
    )
    
    local missing_vars=()
    
    for var in "${required_vars[@]}"; do
        if [ -z "${!var}" ]; then
            missing_vars+=("$var")
        fi
    done
    
    if [ ${#missing_vars[@]} -ne 0 ]; then
        print_error "Missing required environment variables:"
        printf '%s\n' "${missing_vars[@]}"
        exit 1
    fi
    
    print_success "Environment variables validated"
}

# Deploy to Digital Ocean
deploy_app() {
    print_status "Deploying to Digital Ocean App Platform..."
    
    # Update app.yaml with current git repo
    local repo_url=$(git remote get-url origin 2>/dev/null || git remote get-url ekona-github 2>/dev/null || echo "")
    if [ -z "$repo_url" ]; then
        print_error "Git repository not found. Please initialize git and add a remote."
        exit 1
    fi
    
    # Extract repo info (assuming GitHub)
    local repo_path=$(echo "$repo_url" | sed 's/.*github.com[:/]\([^.]*\).*/\1/')
    
    # Create or update the app
    if doctl apps list | grep -q "ekona-slide-creator"; then
        print_status "Updating existing app..."
        local app_id=$(doctl apps list --format ID,Spec.Name --no-header | grep "ekona-slide-creator" | awk '{print $1}')
        doctl apps update "$app_id" --spec .do/app.yaml
    else
        print_status "Creating new app..."
        doctl apps create --spec .do/app.yaml
    fi
    
    print_success "Deployment initiated"
    print_status "Monitor deployment progress at: https://cloud.digitalocean.com/apps"
}

# Set up custom domain (optional)
setup_domain() {
    read -p "Do you want to set up a custom domain? (y/n): " -n 1 -r
    echo
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        read -p "Enter your domain name (e.g., slides.ekona.com): " domain
        print_status "Setting up domain: $domain"
        
        local app_id=$(doctl apps list --format ID,Spec.Name --no-header | grep "ekona-slide-creator" | awk '{print $1}')
        
        if [ -n "$app_id" ]; then
            print_status "Add the following DNS records to your domain:"
            echo "Type: CNAME"
            echo "Name: @ (or your subdomain)"
            echo "Value: (will be provided after app deployment)"
            print_warning "You'll need to configure this in your DNS provider after deployment completes"
        fi
    fi
}

# Main deployment process
main() {
    print_status "Starting Digital Ocean deployment for ekona Slide Creator"
    echo "=================================================="
    
    # Pre-deployment checks
    check_doctl
    check_auth
    check_env
    validate_env
    
    # Deploy
    deploy_app
    
    # Optional domain setup
    setup_domain
    
    echo "=================================================="
    print_success "Deployment process completed!"
    print_status "Next steps:"
    echo "1. Monitor your deployment at: https://cloud.digitalocean.com/apps"
    echo "2. Configure your domain DNS if using custom domain"
    echo "3. Test your application once deployment is complete"
    echo "4. Set up monitoring and alerts in the Digital Ocean dashboard"
}

# Run main function
main "$@"