# Mixed Content Error Fix

## Problem Summary

The CapitolScope frontend was experiencing a "Mixed Content" error when loading the dashboard:

```
Mixed Content: The page at 'https://capitolscope.chrislawrence.ca/' was loaded over HTTPS, 
but requested an insecure XMLHttpRequest endpoint 
'http://capitolscope.chrislawrence.ca/api/v1/trades/?page=1&limit=10'. 
This request has been blocked; the content must be served over HTTPS.
```

## Root Cause

1. **Frontend API Call**: The frontend calls `/api/v1/trades?page=1&limit=10` (without trailing slash)
2. **Backend Route Definition**: The backend route was defined as `@router.get("/")` which requires a trailing slash
3. **FastAPI Redirect**: FastAPI automatically redirects `/api/v1/trades` → `/api/v1/trades/` (307 redirect)
4. **Incorrect Scheme**: The redirect URL was generated with `http://` instead of `https://`, causing the mixed content error

## Solution Implemented

**Changed the backend route definition** from requiring a trailing slash to accepting requests without trailing slash:

**File**: `app/src/api/trades.py`
- **Before**: `@router.get("/")` 
- **After**: `@router.get("")`

This change allows the route to match `/api/v1/trades` directly without requiring a redirect, eliminating the mixed content issue.

## Files Modified

- `app/src/api/trades.py` - Changed route definition from `"/"` to `""`

## Testing

After deploying this change:
1. The frontend should successfully load dashboard data
2. No more mixed content errors in the browser console
3. API requests should complete successfully over HTTPS

## Alternative Solutions Considered

1. **Fix Frontend**: Change frontend to use trailing slash (`/api/v1/trades/`)
   - Rejected: Less flexible, requires frontend changes

2. **Add Middleware**: Configure FastAPI to properly respect `X-Forwarded-Proto` header
   - Rejected: More complex, route fix is simpler

3. **Configure Reverse Proxy**: Ensure proper header forwarding
   - Note: Uvicorn already has `--proxy-headers` enabled, but FastAPI redirects don't use forwarded headers correctly

## Prevention

To prevent similar issues in the future:
- Define API routes without trailing slashes when possible
- Test API endpoints with both trailing slash and without
- Monitor browser console for mixed content warnings in production

