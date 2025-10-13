#!/bin/bash
# Test Cloud Run worker setup locally

echo "🌐 Starting CapitolScope with Cloud Run worker simulation..."
echo ""

# Start with cloud-run profile
docker-compose -p capitolscope-dev --profile cloud-run up --build -d

echo ""
echo "⏳ Waiting for services to start..."
sleep 15

echo ""
echo "📋 Service Status:"
docker-compose -p capitolscope-dev ps

echo ""
echo "🔍 Testing Cloud Run worker..."

# Test health endpoint
echo "Testing health endpoint..."
curl -f http://localhost:8082/health || echo "Health check failed"

echo ""
echo "Testing detailed health endpoint..."
curl -f http://localhost:8082/health/detailed || echo "Detailed health check failed"

echo ""
echo "Testing task execution..."
curl -X POST http://localhost:8082/tasks/execute \
  -H "Content-Type: application/json" \
  -d '{
    "task_name": "health_check_congress_api",
    "parameters": {},
    "priority": 5
  }' || echo "Task execution failed"

echo ""
echo "Testing queue status..."
curl -f http://localhost:8082/admin/queue-status || echo "Queue status check failed"

echo ""
echo "✅ Cloud Run worker test complete!"
echo "🌐 API available at: http://localhost:8001"
echo "🌐 Worker available at: http://localhost:8082"
echo "🌐 Frontend available at: http://localhost:5173"
echo ""
echo "📝 Cloud Run Worker Endpoints:"
echo "  • Health: http://localhost:8082/health"
echo "  • Detailed Health: http://localhost:8082/health/detailed"
echo "  • Execute Task: POST http://localhost:8082/tasks/execute"
echo "  • Queue Status: http://localhost:8082/admin/queue-status"
echo ""
echo "To stop: docker-compose -p capitolscope-dev --profile cloud-run down"



