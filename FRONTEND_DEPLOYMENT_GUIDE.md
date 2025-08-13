# CapitolScope Frontend Deployment Guide

This guide covers deploying the React frontend to Google Cloud Platform using two strategies:
1. **Cloud Storage** (Static hosting)
2. **Cloud Run** (Containerized with SSR support)

## Prerequisites

- Google Cloud SDK installed and configured
- Docker installed (for Cloud Run deployment)
- Node.js 18+ installed
- Access to the CapitolScope project

## Strategy 1: Cloud Storage Deployment (Recommended for Static Sites)

### Quick Deploy
```bash
# Make script executable
chmod +x deploy_frontend_cloud_storage.sh

# Deploy to Cloud Storage
./deploy_frontend_cloud_storage.sh
```

### Manual Steps
```bash
# Navigate to frontend
cd frontend

# Build with API URL
VITE_API_URL=https://capitolscope-api-k23f5lpvca-uw.a.run.app npm run build

# Deploy to existing bucket
gcloud storage cp -r dist/* gs://capitolscope-frontend-capitolscope/

# Make files publicly readable
gcloud storage objects update gs://capitolscope-frontend-capitolscope/** --add-acl-grant=entity=AllUsers,role=READER
```

### Benefits
- ✅ Fast loading times
- ✅ Cost-effective
- ✅ Simple deployment
- ✅ Global CDN

### Limitations
- ❌ No server-side rendering
- ❌ Limited dynamic features

## Strategy 2: Cloud Run Deployment (Recommended for SSR)

### Quick Deploy
```bash
# Make script executable
chmod +x deploy_frontend_cloud_run.sh

# Deploy to Cloud Run
./deploy_frontend_cloud_run.sh
```

### Manual Steps
```bash
# Navigate to frontend
cd frontend

# Build Docker image
docker build -f Dockerfile.prod \
  --build-arg VITE_API_URL=https://capitolscope-api-k23f5lpvca-uw.a.run.app \
  -t us-west1-docker.pkg.dev/capitolscope/capitolscope/capitolscope-frontend:latest \
  .

# Deploy to Cloud Run
gcloud run deploy capitolscope-frontend \
  --image us-west1-docker.pkg.dev/capitolscope/capitolscope/capitolscope-frontend:latest \
  --region us-west1 --allow-unauthenticated \
  --port 80 --memory 512Mi --cpu 1
```

### Benefits
- ✅ Server-side rendering support
- ✅ Dynamic routing
- ✅ Better SEO
- ✅ More control over server behavior

### Limitations
- ❌ Higher cost
- ❌ More complex deployment
- ❌ Cold start delays

## Troubleshooting

### Run Diagnostics
```bash
cd frontend
chmod +x troubleshoot.sh
./troubleshoot.sh
```

### Common Issues

#### 1. Chart.js Import Errors
```bash
# Check Chart.js installation
npm list chart.js
npm list react-chartjs-2

# Reinstall if needed
npm uninstall chart.js react-chartjs-2
npm install chart.js@^4.5.0 react-chartjs-2@^5.3.0
```

#### 2. Build Failures
```bash
# Clear cache and rebuild
rm -rf node_modules/.vite
rm -rf dist/
npm ci
npm run build -- --force
```

#### 3. API Connection Issues
- Verify `VITE_API_URL` is correct
- Check API service is running
- Test API endpoint directly

#### 4. CORS Issues
- Ensure API has proper CORS headers
- Check domain configuration

### Environment Variables

| Variable | Description | Default |
|----------|-------------|---------|
| `VITE_API_URL` | Backend API URL | `http://localhost:8000` |
| `NODE_ENV` | Environment | `production` |

## File Structure

```
frontend/
├── src/
│   ├── components/
│   │   ├── charts/
│   │   │   └── DoughnutChart.tsx    # Chart.js components
│   │   └── ...
│   ├── App.tsx                      # Main app with routing
│   └── ...
├── vite.config.ts                   # Vite configuration
├── package.json                     # Dependencies
├── Dockerfile.prod                  # Production Dockerfile
├── nginx.conf                       # Nginx configuration
└── troubleshoot.sh                  # Troubleshooting script
```

## Key Features

### Routing
- `/` - Landing page
- `/dashboard` - Main dashboard
- `/trades` - Trade browser
- `/members` - Member browser
- `/analytics` - Analytics page
- `/data-quality` - Data quality metrics

### Charts
- Doughnut charts using Chart.js
- Responsive design
- Dark mode support
- Interactive tooltips

### Authentication
- Login/Register pages
- Protected routes
- JWT token management
- Password reset functionality

## Monitoring

### Cloud Storage
- Monitor bucket access logs
- Check file permissions
- Verify CDN cache

### Cloud Run
- Monitor service logs
- Check performance metrics
- Monitor cold starts

## Rollback Strategy

### Cloud Storage
```bash
# Restore from backup or previous version
gcloud storage cp -r gs://capitolscope-frontend-capitolscope/backup/* gs://capitolscope-frontend-capitolscope/
```

### Cloud Run
```bash
# Deploy previous image version
gcloud run deploy capitolscope-frontend \
  --image us-west1-docker.pkg.dev/capitolscope/capitolscope/capitolscope-frontend:previous \
  --region us-west1
```

## Security Considerations

1. **API URL**: Use HTTPS in production
2. **CORS**: Configure proper CORS headers
3. **Authentication**: Implement proper JWT validation
4. **Environment Variables**: Never commit secrets
5. **Dependencies**: Regular security updates

## Performance Optimization

1. **Code Splitting**: Implemented in Vite config
2. **Asset Optimization**: Minified and compressed
3. **Caching**: Proper cache headers
4. **CDN**: Global content delivery
5. **Bundle Analysis**: Monitor bundle sizes

## Support

For issues or questions:
1. Run `./troubleshoot.sh` first
2. Check browser console for errors
3. Verify API connectivity
4. Review deployment logs
