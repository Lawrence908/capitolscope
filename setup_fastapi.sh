#!/bin/bash

# CapitolScope FastAPI Setup Script
# This script helps set up the new FastAPI + Supabase infrastructure

set -e

echo "🚀 Setting up CapitolScope with FastAPI + Supabase..."

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

# Check if running from project root
if [ ! -f "app/pyproject.toml" ]; then
    print_error "Please run this script from the project root directory"
    exit 1
fi

# Step 1: Environment Configuration
print_status "Step 1: Setting up environment configuration..."

if [ ! -f ".env" ]; then
    print_warning ".env file not found. Please create one based on the template:"
    echo ""
    echo "Copy and customize the following template:"
    echo "=================================="
    cat << 'EOF'
# SUPABASE CONFIGURATION
SUPABASE_URL=https://your-project.supabase.co
SUPABASE_KEY=your-supabase-anon-key
SUPABASE_JWT_SECRET=your-jwt-secret
SUPABASE_PROJECT_REF=your-project-ref
SUPABASE_PASSWORD=your-database-password

# APPLICATION SETTINGS
ENVIRONMENT=development
DEBUG=true
SECRET_KEY=your-super-secret-key-change-this
API_VERSION=v1

# EXTERNAL APIS
ALPHA_VANTAGE_API_KEY=your_alpha_vantage_key_here

# REDIS & BACKGROUND TASKS
REDIS_PASSWORD=devpassword

# EMAIL SERVICES (optional)
SENDGRID_API_KEY=your_sendgrid_key_here
SENDGRID_FROM_EMAIL=noreply@capitolscope.com

# STRIPE PAYMENT (optional)
STRIPE_SECRET_KEY=sk_test_your_stripe_secret_key_here
STRIPE_PUBLISHABLE_KEY=pk_test_your_stripe_publishable_key_here

# MONITORING (optional)
SENTRY_DSN=your_sentry_dsn_here
EOF
    echo "=================================="
    echo ""
    read -p "Press Enter after creating your .env file..."
fi

# Step 2: Install dependencies
print_status "Step 2: Installing Python dependencies..."

if command -v uv &> /dev/null; then
    print_status "Using uv package manager..."
    cd app && uv pip install -e . && cd ..
else
    print_warning "uv not found, falling back to pip..."
    cd app && pip install -e . && cd ..
fi

print_success "Dependencies installed successfully"

# Step 3: Create Alembic migration directory
print_status "Step 3: Setting up database migrations..."

if [ ! -d "alembic" ]; then
    print_status "Creating Alembic migration directory..."
    alembic init alembic
    print_success "Alembic initialized"
else
    print_warning "Alembic directory already exists"
fi

# Step 4: Start services
print_status "Step 4: Starting services with Docker Compose..."

# Check if Docker is running
if ! docker info > /dev/null 2>&1; then
    print_error "Docker is not running. Please start Docker and try again."
    exit 1
fi

# Start services
print_status "Starting Redis and application services..."
docker-compose -p capitolscope-dev up -d redis-dev

print_success "Redis started successfully"

# Step 5: Test basic setup
print_status "Step 5: Testing basic setup..."

# Wait a moment for services to start
sleep 5

# Test if we can import the main modules
cd app/src
if python -c "from core.config import settings; print('✓ Configuration loaded'); from core.logging import configure_logging; print('✓ Logging configured')" 2>/dev/null; then
    print_success "Basic imports working correctly"
else
    print_error "There are issues with the basic setup. Please check the error messages above."
    cd ../..
    exit 1
fi
cd ../..

# Step 6: Display next steps
print_success "FastAPI setup completed successfully! 🎉"
echo ""
echo "Next steps:"
echo "==========="
echo "1. 📝 Configure your Supabase credentials in .env"
echo "2. 🗄️  Set up your Supabase database tables (we'll help with this next)"
echo "3. 🚀 Start the development server:"
echo "   docker-compose -p capitolscope-dev up --build"
echo ""
echo "4. 📖 Access API documentation at:"
echo "   http://localhost:8000/docs"
echo ""
echo "5. 🔍 Health check endpoint:"
echo "   http://localhost:8000/health"
echo ""
echo "The following services will be available:"
echo "• FastAPI application: http://localhost:8000"
echo "• API documentation: http://localhost:8000/docs"
echo "• Health checks: http://localhost:8000/health"
echo ""
print_warning "Make sure to configure your Supabase credentials before starting the full application!"

# Step 7: Backup old files
print_status "Step 7: Backing up old project files..."

# Create backup directory
backup_dir="backup_old_structure_$(date +%Y%m%d_%H%M%S)"
mkdir -p "$backup_dir"

# Move old files that might conflict
if [ -f "Dockerfile" ]; then
    mv Dockerfile "$backup_dir/"
    print_status "Moved old Dockerfile to backup"
fi

if [ -f "requirements.txt" ]; then
    cp requirements.txt "$backup_dir/"
    print_status "Backed up old requirements.txt"
fi

if [ -d "src/database" ]; then
    cp -r src/database "$backup_dir/"
    print_status "Backed up old database module"
fi

print_success "Old files backed up to $backup_dir/"

echo ""
print_success "Setup complete! You're ready to start building with FastAPI + Supabase! 🚀" 