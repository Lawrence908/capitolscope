#!/bin/bash
# Test ONLY the Cloud Run worker locally (simplified)

echo "🌐 Testing Cloud Run Worker Only..."
echo ""

# Clean up any existing containers
echo "🧹 Cleaning up existing containers..."
docker-compose -f docker-compose.cloud-worker.yml down
docker system prune -f

echo ""
echo "🔧 Building and starting Cloud Run worker..."
docker-compose -f docker-compose.cloud-worker.yml up --build -d

echo ""
echo "⏳ Waiting for services to start..."
sleep 20

echo ""
echo "📋 Service Status:"
docker-compose -f docker-compose.cloud-worker.yml ps

echo ""
echo "🔍 Testing Cloud Run worker endpoints..."

# Test health endpoint
echo ""
echo "1. Testing basic health endpoint..."
curl -f http://localhost:8082/health && echo "" || echo "❌ Basic health check failed"

echo ""
echo "2. Testing detailed health endpoint..."
curl -f http://localhost:8082/health/detailed && echo "" || echo "❌ Detailed health check failed"

echo ""
echo "3. Testing task execution..."
curl -X POST http://localhost:8082/tasks/execute \
  -H "Content-Type: application/json" \
  -d '{
    "task_name": "system_health_check",
    "parameters": {},
    "priority": 5
  }' && echo "" || echo "❌ Task execution failed"

echo ""
echo "4. Testing queue status..."
curl -f http://localhost:8082/admin/queue-status && echo "" || echo "❌ Queue status check failed"

echo ""
echo "📊 Checking container logs..."
echo "Worker logs (last 20 lines):"
docker-compose -f docker-compose.cloud-worker.yml logs --tail=20 worker

echo ""
echo "✅ Cloud Run worker test complete!"
echo ""
echo "📝 Available endpoints:"
echo "  • Health: http://localhost:8082/health"
echo "  • Detailed Health: http://localhost:8082/health/detailed"
echo "  • Execute Task: POST http://localhost:8082/tasks/execute"
echo "  • Queue Status: http://localhost:8082/admin/queue-status"
echo ""
echo "📊 View logs: docker-compose -f docker-compose.cloud-worker.yml logs -f worker"
echo "🛑 To stop: docker-compose -f docker-compose.cloud-worker.yml down"



