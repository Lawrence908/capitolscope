#!/bin/bash
# Test traditional Celery setup locally

echo "🔧 Starting CapitolScope with traditional Celery workers..."
echo ""

# Start with Celery profile
docker-compose -p capitolscope-dev --profile celery up --build -d

echo ""
echo "⏳ Waiting for services to start..."
sleep 15

echo ""
echo "📋 Service Status:"
docker-compose -p capitolscope-dev ps

echo ""
echo "🔍 Testing Celery worker..."

# Test Celery task execution
docker-compose -p capitolscope-dev exec capitolscope python -c "
import sys
sys.path.append('src')
from background.tasks import health_check_congress_api
result = health_check_congress_api.delay()
print(f'Task submitted: {result.id}')
try:
    output = result.get(timeout=30)
    print(f'Task result: {output}')
except Exception as e:
    print(f'Task failed: {e}')
"

echo ""
echo "📊 Celery Status:"
docker-compose -p capitolscope-dev exec worker celery -A background.celery_app inspect stats

echo ""
echo "✅ Traditional Celery test complete!"
echo "🌐 API available at: http://localhost:8001"
echo "🌐 Frontend available at: http://localhost:5173"
echo ""
echo "To stop: docker-compose -p capitolscope-dev --profile celery down"



