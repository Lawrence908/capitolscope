#!/bin/bash

# CapitolScope Docker Aliases
# Source this file in your ~/.bashrc or ~/.zshrc: source /path/to/docker-aliases.sh

# Build and run containers with file watching enabled
alias capitol-build='docker-compose -p capitolscope-dev up --build --watch'

# Display logs for running containers
alias capitol-logs='docker-compose -p capitolscope-dev logs -f'

# Stop all containers
alias capitol-stop='docker-compose -p capitolscope-dev down'

# Restart just the main app container
alias capitol-restart='docker-compose -p capitolscope-dev restart capitolscope'

# Execute bash in the running container
alias capitol-shell='docker-compose -p capitolscope-dev exec capitolscope bash'

# Run database migrations
alias capitol-migrate='docker-compose -p capitolscope-dev exec capitolscope python -m alembic upgrade head'

# View only app logs
alias capitol-app-logs='docker-compose -p capitolscope-dev logs -f capitolscope'

# View only worker logs  
alias capitol-worker-logs='docker-compose -p capitolscope-dev logs -f worker'

echo "CapitolScope Docker aliases loaded:"
echo "  capitol-build     - Build and run with file watching"
echo "  capitol-logs      - Show all container logs"
echo "  capitol-stop      - Stop all containers"
echo "  capitol-restart   - Restart main app"
echo "  capitol-shell     - Open shell in container"
echo "  capitol-migrate   - Run database migrations"
echo "  capitol-app-logs  - Show only app logs"
echo "  capitol-worker-logs - Show only worker logs" 