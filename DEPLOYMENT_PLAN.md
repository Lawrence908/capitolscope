# CapitolScope Deployment Plan

## Current Status
- ✅ Backend API deployed successfully to Cloud Run (us-west1)
- ✅ Supabase database connection working
- ❌ Frontend build failing due to React version compatibility issues
- ❌ React Router exports not compatible with current React setup

## Problem Analysis
The frontend build is failing because:
1. React Router expects specific React exports that aren't available
2. Version mismatches between React, React Router, and other dependencies
3. The build process is trying to use development builds instead of production builds

## Deployment Strategies (Ranked by Priority)

### Strategy 1: Cloud Storage Static Site (RECOMMENDED)
**Pros:** Fastest to deploy, no build issues, works with any frontend
**Cons:** No server-side rendering

**Steps:**
1. Build frontend locally (where it works)
2. Upload static files to Cloud Storage
3. Configure as public website
4. Map custom domain

### Strategy 2: Cloud Run Frontend Container
**Pros:** Full control, can add server-side features later
**Cons:** More complex, requires fixing build issues

**Steps:**
1. Fix React compatibility issues
2. Create production Dockerfile
3. Deploy to Cloud Run
4. Configure custom domain

### Strategy 3: Firebase Hosting
**Pros:** Optimized for React apps, automatic HTTPS
**Cons:** Additional service to manage

**Steps:**
1. Set up Firebase project
2. Configure hosting
3. Deploy static build
4. Map custom domain

## Immediate Action Plan

### Phase 1: Get Frontend Live (Today)
1. **Use working local build**
   - Since the app works locally, use that build
   - Copy `dist/` folder from local development
   - Upload to Cloud Storage

2. **Deploy to Cloud Storage**
   ```bash
   # Create bucket
   gcloud storage buckets create gs://capitolscope-frontend-capitolscope --location=US-WEST1 --uniform-bucket-level-access
   
   # Upload files (from working local build)
   gcloud storage cp -r frontend/dist/* gs://capitolscope-frontend-capitolscope/
   
   # Make public
   gcloud storage buckets update gs://capitolscope-frontend-capitolscope --web-main-page-suffix=index.html --web-error-page=index.html
   gcloud storage objects update gs://capitolscope-frontend-capitolscope/** --add-acl-grant=AllUsers:READER
   ```

3. **Configure custom domain**
   - Use Cloud Run "Custom domains" feature
   - Point subdomain to Cloud Storage website URL

### Phase 2: Fix Build Issues (Next)
1. **Investigate React compatibility**
   - Check exact React version that works locally
   - Update package.json to match working versions
   - Test build process step by step

2. **Alternative: Use different build tool**
   - Try Vite with different configuration
   - Consider switching to Create React App temporarily
   - Use Parcel as alternative bundler

### Phase 3: Optimize (Future)
1. **Move to Cloud Run frontend**
2. **Add server-side rendering**
3. **Implement CDN caching**

## Current Working URLs
- **Backend API:** https://capitolscope-api-k23f5lpvca-uw.a.run.app
- **API Health Check:** https://capitolscope-api-k23f5lpvca-uw.a.run.app/health
- **API Docs:** https://capitolscope-api-k23f5lpvca-uw.a.run.app/docs

## Environment Variables Needed
```bash
# Supabase (already working)
SUPABASE_URL=https://<your>.supabase.co
SUPABASE_KEY=<anon_key>
SUPABASE_SERVICE_ROLE_KEY=<service_role_key>
SUPABASE_PASSWORD=<db_password>
SUPABASE_JWT_SECRET=<jwt_secret>

# Frontend API URL
VITE_API_URL=https://capitolscope-api-k23f5lpvca-uw.a.run.app
```

## Next Steps
1. **Immediate:** Deploy working local build to Cloud Storage
2. **Today:** Configure custom domain mapping
3. **This week:** Fix build issues for future deployments
4. **Future:** Optimize and add features

## Troubleshooting Commands
```bash
# Check backend status
gcloud run services describe capitolscope-api --region us-west1

# Check frontend bucket
gcloud storage ls gs://capitolscope-frontend-capitolscope/

# Test API endpoints
curl https://capitolscope-api-k23f5lpvca-uw.a.run.app/health
curl https://capitolscope-api-k23f5lpvca-uw.a.run.app/api/v1/trades
```

