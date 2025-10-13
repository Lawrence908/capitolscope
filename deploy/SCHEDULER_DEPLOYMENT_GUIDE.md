# 🚀 CapitolScope Scheduler Deployment Guide

This guide provides step-by-step instructions for deploying the production-ready scheduler and cron system.

## 📋 Prerequisites

- Ubuntu/Debian Linux server
- PostgreSQL database
- Redis server
- Python 3.8+
- Root or sudo access

## 🛠️ Installation Steps

### Step 1: Server Setup

```bash
# Update system packages
sudo apt update && sudo apt upgrade -y

# Install required packages
sudo apt install -y redis-server postgresql postgresql-contrib nginx supervisor python3-pip python3-venv git

# Create application user
sudo useradd -m -s /bin/bash capitolscope

# Create required directories
sudo mkdir -p /opt/capitolscope /var/log/capitolscope /var/run/capitolscope /var/lib/capitolscope /opt/capitolscope/backups
sudo chown capitolscope:capitolscope /opt/capitolscope /var/log/capitolscope /var/run/capitolscope /var/lib/capitolscope /opt/capitolscope/backups
```

### Step 2: Application Deployment

```bash
# Clone repository
sudo -u capitolscope git clone https://github.com/your-repo/CapitolScope.git /opt/capitolscope
cd /opt/capitolscope

# Create virtual environment
sudo -u capitolscope python3 -m venv .venv

# Install dependencies
sudo -u capitolscope .venv/bin/pip install -r requirements.txt

# Install additional monitoring dependencies
sudo -u capitolscope .venv/bin/pip install flower psutil redis
```

### Step 3: Environment Configuration

```bash
# Copy environment template
sudo -u capitolscope cp .env.example .env

# Edit configuration (update database URLs, Redis URLs, etc.)
sudo -u capitolscope nano .env
```

### Step 4: Database Setup

```bash
# Create database and user
sudo -u postgres createdb capitolscope
sudo -u postgres createuser capitolscope

# Set password and permissions
sudo -u postgres psql -c "ALTER USER capitolscope WITH PASSWORD 'your_secure_password';"
sudo -u postgres psql -c "GRANT ALL PRIVILEGES ON DATABASE capitolscope TO capitolscope;"

# Run migrations
cd /opt/capitolscope
sudo -u capitolscope .venv/bin/python -m alembic upgrade head
```

### Step 5: Install Systemd Services

```bash
# Install service files
sudo cp deploy/systemd/*.service /etc/systemd/system/
sudo systemctl daemon-reload

# Make scripts executable
chmod +x scripts/*.sh

# Install Celery services
./scripts/celery_management.sh install-services
```

### Step 6: Install Cron Jobs

```bash
# Install cron jobs
sudo cp deploy/cron/capitolscope-tasks.cron /etc/cron.d/capitolscope-tasks

# Verify cron jobs
sudo crontab -l -u capitolscope
```

### Step 7: Start Services

```bash
# Start all Celery services
./scripts/celery_management.sh start-all

# Check status
./scripts/celery_management.sh status

# Test task execution
./scripts/celery_management.sh test
```

## 🔧 Configuration Files

### Environment Variables (.env)

```bash
# Database
DATABASE_URL=postgresql://capitolscope:password@localhost:5432/capitolscope

# Redis
CELERY_BROKER_URL=redis://localhost:6379/0
CELERY_RESULT_BACKEND=redis://localhost:6379/1

# Email (for notifications)
SMTP_HOST=smtp.gmail.com
SMTP_PORT=587
SMTP_USERNAME=your-email@gmail.com
SMTP_PASSWORD=your-app-password

# Security
SECRET_KEY=your-very-secure-secret-key

# Logging
LOG_LEVEL=INFO
```

### Redis Configuration (/etc/redis/redis.conf)

```conf
# Memory settings
maxmemory 512mb
maxmemory-policy allkeys-lru

# Persistence
save 900 1
save 300 10
save 60 10000

# Security
requirepass your_redis_password
```

### PostgreSQL Configuration

```sql
-- Optimize for Celery workloads
ALTER SYSTEM SET shared_buffers = '256MB';
ALTER SYSTEM SET effective_cache_size = '1GB';
ALTER SYSTEM SET maintenance_work_mem = '64MB';
ALTER SYSTEM SET checkpoint_completion_target = 0.9;
ALTER SYSTEM SET wal_buffers = '16MB';
SELECT pg_reload_conf();
```

## 📊 Monitoring & Management

### Check Service Status

```bash
# Overall system status
./scripts/celery_management.sh status

# Check queue status
./scripts/celery_management.sh queue-status

# Inspect workers
./scripts/celery_management.sh inspect
```

### View Logs

```bash
# Worker logs
./scripts/celery_management.sh logs-worker

# Beat logs
./scripts/celery_management.sh logs-beat

# System logs
tail -f /var/log/capitolscope/health_check.log
```

### Flower Monitoring Dashboard

```bash
# Start Flower
./scripts/celery_management.sh monitor

# Access at http://your-server:5555
# Default login: admin / secure_password
```

## 🚨 Troubleshooting

### Common Issues

1. **Worker not starting**
   ```bash
   # Check logs
   sudo journalctl -u capitolscope-celery-worker -f
   
   # Check permissions
   sudo ls -la /var/log/capitolscope/
   sudo ls -la /var/run/capitolscope/
   ```

2. **Tasks failing**
   ```bash
   # Test individual task
   ./scripts/celery_management.sh test
   
   # Check queue status
   ./scripts/celery_management.sh queue-status
   ```

3. **Database connection issues**
   ```bash
   # Test database connection
   sudo -u capitolscope psql capitolscope -c "SELECT 1;"
   
   # Check database logs
   sudo tail -f /var/log/postgresql/postgresql-*.log
   ```

4. **Redis connection issues**
   ```bash
   # Test Redis connection
   redis-cli ping
   
   # Check Redis logs
   sudo tail -f /var/log/redis/redis-server.log
   ```

### Performance Tuning

1. **Worker Concurrency**
   - Edit systemd service file
   - Adjust `--concurrency` parameter based on CPU cores

2. **Queue Routing**
   - Monitor queue lengths with `queue-status`
   - Adjust task routing in `production_celery.py`

3. **Memory Usage**
   - Monitor with `htop` or `free -h`
   - Adjust worker memory limits in systemd services

## 🔒 Security Considerations

1. **File Permissions**
   ```bash
   # Secure log files
   sudo chmod 640 /var/log/capitolscope/*.log
   sudo chown capitolscope:adm /var/log/capitolscope/*.log
   ```

2. **Redis Security**
   - Set strong password
   - Bind to localhost only
   - Disable dangerous commands

3. **Database Security**
   - Use strong passwords
   - Limit network access
   - Regular security updates

## 📈 Scaling

### Horizontal Scaling

1. **Multiple Workers**
   ```bash
   # Add more worker processes
   sudo systemctl edit capitolscope-celery-worker
   # Increase --concurrency parameter
   ```

2. **Dedicated Queue Workers**
   ```bash
   # Create specialized workers for specific queues
   # Copy and modify systemd service files
   ```

### Vertical Scaling

1. **Increase Resources**
   - Add more RAM
   - Add more CPU cores
   - Use faster storage (SSD)

2. **Database Optimization**
   - Tune PostgreSQL settings
   - Add database indexes
   - Consider connection pooling

## 🔄 Maintenance

### Daily Tasks
- Monitor logs
- Check disk space
- Verify backups

### Weekly Tasks
- Review queue performance
- Update dependencies
- Security patches

### Monthly Tasks
- Database maintenance
- Log rotation
- Performance review

## 📞 Support

For issues and questions:
- Check logs first
- Review this deployment guide
- Submit issues to the repository
- Contact the development team

---

**Note**: Remember to customize configurations for your specific environment and security requirements.



