# FastAPI + Supabase Migration Guide

This document outlines the migration from the old SQLite + Flask/Django setup to the new **FastAPI + Supabase** architecture for CapitolScope.

## 🚀 **What Changed**

### **Old Architecture:**
- ❌ SQLite database (local, hard to scale)
- ❌ Basic Django/Flask setup
- ❌ Manual cron jobs
- ❌ No proper async support
- ❌ Limited authentication

### **New Architecture:**
- ✅ **Supabase PostgreSQL** (cloud, scalable, managed)
- ✅ **FastAPI** (modern, async, automatic docs)
- ✅ **Celery + Redis** (background tasks)
- ✅ **Multi-stage Docker** with `uv` package manager
- ✅ **Supabase Auth** (built-in user management)
- ✅ **Structured logging** with `structlog`
- ✅ **Modern async/await** throughout

## 📁 **New Project Structure**

```
capitolscope/
├── app/
│   ├── src/                          # Application source code
│   │   ├── main.py                   # FastAPI application entry point
│   │   ├── core/                     # Core application modules
│   │   │   ├── config.py            # Pydantic settings (Supabase config)
│   │   │   ├── database.py          # Async SQLAlchemy + Supabase
│   │   │   └── logging.py           # Structured logging setup
│   │   ├── api/                      # API endpoints
│   │   │   ├── health.py            # Health check endpoints
│   │   │   ├── auth.py              # Authentication (Supabase)
│   │   │   ├── trades.py            # Congressional trades API
│   │   │   └── members.py           # Congress members API
│   │   ├── models/                   # SQLAlchemy + Pydantic models
│   │   ├── services/                 # Business logic
│   │   └── background/               # Celery tasks
│   ├── Dockerfile                    # Multi-stage Docker build
│   └── pyproject.toml               # Modern Python dependencies
├── docker-compose.yml               # Dev environment (FastAPI + Redis)
├── alembic.ini                      # Database migrations
├── alembic/                         # Migration scripts
└── .env                            # Environment configuration
```

## 🔧 **Migration Steps**

### **1. Quick Setup**
```bash
# Run the setup script
./setup_fastapi.sh
```

### **2. Manual Setup**
If you prefer manual setup:

```bash
# 1. Install dependencies
pip install -e .

# 2. Create .env file (see template below)
cp .env.template .env
# Edit .env with your Supabase credentials

# 3. Start services
docker-compose -p capitolscope-dev up --build

# 4. Access API docs
open http://localhost:8000/docs
```

## 🔐 **Environment Configuration**

Create a `.env` file with your Supabase credentials:

```bash
# SUPABASE CONFIGURATION (REQUIRED)
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

# STRIPE PAYMENT (optional) 
STRIPE_SECRET_KEY=sk_test_your_stripe_secret_key_here

# MONITORING (optional)
SENTRY_DSN=your_sentry_dsn_here
```

## 🗄️ **Database Migration**

### **From SQLite to Supabase:**

1. **Set up Supabase Project:**
   - Create account at [supabase.com](https://supabase.com)
   - Create new project
   - Get credentials from Settings > API

2. **Run Database Migrations:**
   ```bash
   # Generate initial migration
   alembic revision --autogenerate -m "Initial tables"
   
   # Apply migrations to Supabase
   alembic upgrade head
   ```

3. **Migrate Existing Data:**
   ```bash
   # Run data migration script (to be created)
   python scripts/migrate_sqlite_to_supabase.py
   ```

## 🔄 **Development Workflow**

### **Starting Development:**
```bash
# Start all services
docker-compose -p capitolscope-dev up --build

# Or start individual services
docker-compose -p capitolscope-dev up capitolscope  # API only
docker-compose -p capitolscope-dev up worker        # Background worker
```

### **API Development:**
```bash
# The FastAPI app runs with hot reload
# Edit files in app/src/ and see changes immediately

# API documentation available at:
http://localhost:8000/docs       # Swagger UI
http://localhost:8000/redoc      # ReDoc
```

### **Database Changes:**
```bash
# Create migration after model changes
alembic revision --autogenerate -m "Add new table"

# Apply migration
alembic upgrade head
```

## 📊 **Key Benefits**

### **Performance:**
- ⚡ **Async/await** throughout the application
- 🚀 **Connection pooling** for database connections
- 📦 **Redis caching** for improved response times
- 🔄 **Background tasks** for data ingestion

### **Developer Experience:**
- 📖 **Automatic API documentation** at `/docs`
- 🔧 **Hot reload** in development
- 🧪 **Type hints** and validation with Pydantic
- 📝 **Structured logging** for better debugging

### **Scalability:**
- ☁️ **Supabase** handles database scaling
- 🐳 **Docker containers** for easy deployment
- 🔀 **Celery workers** for horizontal scaling
- 📈 **Built-in monitoring** and health checks

### **Security:**
- 🔐 **Supabase Auth** with JWT tokens
- 🛡️ **Input validation** with Pydantic
- 🔒 **Environment-based configuration**
- 🏥 **Health checks** for monitoring

## 🆚 **Migration Comparison**

| Feature | Old (SQLite + Flask) | New (Supabase + FastAPI) |
|---------|---------------------|---------------------------|
| **Database** | SQLite (local file) | Supabase PostgreSQL (cloud) |
| **API Framework** | Flask/Django | FastAPI |
| **Async Support** | Limited | Full async/await |
| **Authentication** | Custom | Supabase Auth |
| **Documentation** | Manual | Auto-generated |
| **Background Tasks** | Cron jobs | Celery + Redis |
| **Type Safety** | Basic | Full Pydantic validation |
| **Deployment** | Manual | Docker containers |
| **Monitoring** | Basic logging | Structured logs + health checks |
| **Scalability** | Single server | Horizontal scaling ready |

## 🎯 **Next Steps**

After setting up the FastAPI infrastructure:

1. **Database Models** - Design Pydantic models for API validation
2. **Data Migration** - Move existing congressional data to Supabase
3. **API Endpoints** - Implement CAP-10 (Transaction List Page)
4. **Authentication** - Set up Supabase auth integration
5. **Background Tasks** - Implement CAP-25 (Daily Price Data Ingestion)

## 🚨 **Common Issues**

### **Supabase Connection Issues:**
```bash
# Check connection
python -c "from app.src.core.database import test_connection; test_connection()"

# Verify environment variables
python -c "from app.src.core.config import settings; print(settings.database_url)"
```

### **Docker Issues:**
```bash
# Rebuild containers
docker-compose -p capitolscope-dev down
docker-compose -p capitolscope-dev up --build

# Check logs
docker-compose -p capitolscope-dev logs capitolscope
```

### **Import Issues:**
```bash
# Ensure PYTHONPATH is set correctly
export PYTHONPATH=/app/src

# Or use the docker environment
docker-compose -p capitolscope-dev exec capitolscope python -c "import main"
```

---

## 🎉 **You're Ready!**

The FastAPI + Supabase foundation is now set up and ready for implementing the Linear tickets:

- ✅ **CAP-21:** Database Schema Design (foundation complete)
- 🚀 **CAP-24:** Comprehensive Stock Database Setup (ready to implement)
- 🚀 **CAP-25:** Daily Price Data Ingestion System (ready to implement)

**Happy coding with FastAPI + Supabase!** 🚀 