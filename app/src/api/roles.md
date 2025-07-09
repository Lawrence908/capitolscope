```python
# Require admin role
@router.get("/admin-only")
async def admin_endpoint(user: User = Depends(require_admin())):
    return {"message": "Admin access granted"}

# Require specific role
@router.get("/mod-only") 
async def mod_endpoint(user: User = Depends(require_role(["moderator", "admin"]))):
    return {"message": "Moderator+ access granted"}

# Require permission
@router.get("/metrics")
async def metrics(user: User = Depends(require_permission("read:system_metrics"))):
    return {"message": "System metrics"}
```