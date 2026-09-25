"""
Project P4: Containerized Production Application
"""
import time
import uuid
from fastapi import FastAPI, Depends, BackgroundTasks, Request, Response, status
from .config import settings
from .auth import create_access_token, get_current_user, require_role
from .cache import cache
from .tasks import process_audit_log

app = FastAPI(
    title=settings.app_name,
    version="2.0.0",
    debug=settings.debug,
)


@app.middleware("http")
async def request_tracing_middleware(request: Request, call_next):
    """Correlation ID and Latency Middleware."""
    req_id = request.headers.get("X-Request-ID", f"req-{uuid.uuid4().hex[:8]}")
    t0 = time.perf_counter()
    response: Response = await call_next(request)
    elapsed_ms = (time.perf_counter() - t0) * 1000.0
    response.headers["X-Request-ID"] = req_id
    response.headers["X-Response-Time-Ms"] = f"{elapsed_ms:.2f}"
    return response


@app.get("/healthz", tags=["System"])
async def health_check():
    return {
        "status": "healthy",
        "environment": settings.environment,
        "cache_hits": cache.hits,
        "cache_misses": cache.misses,
    }


@app.post("/api/v1/auth/login", tags=["Auth"])
async def login(username: str, role: str = "user"):
    """Generates JWT Bearer access token."""
    token = create_access_token(subject=username, role=role)
    return {"access_token": token, "token_type": "bearer"}


@app.get("/api/v1/user/profile", tags=["User"])
async def get_profile(current_user: dict = Depends(get_current_user)):
    return {
        "username": current_user["sub"],
        "role": current_user["role"],
        "issued_at": current_user["iat"],
    }


@app.get("/api/v1/data/report", tags=["Data"])
async def get_cached_report(
    current_user: dict = Depends(get_current_user),
):
    """Demonstrates Cache-Aside: Returns cached computation if available."""
    cache_key = "report:global_metrics"
    cached_data = cache.get(cache_key)

    if cached_data is not None:
        return {"data": cached_data, "source": "cache"}

    # Simulate expensive computation
    fresh_data = {"active_users": 1540, "daily_revenue": 45200.0, "computed_for": current_user["sub"]}
    cache.set(cache_key, fresh_data, ttl_seconds=60)
    return {"data": fresh_data, "source": "database"}


@app.post("/api/v1/admin/action", tags=["Admin"])
async def admin_action(
    action_name: str,
    background_tasks: BackgroundTasks,
    admin_user: dict = Depends(require_role("admin")),
):
    """Admin-only endpoint with async background audit logging."""
    resource_id = f"res-{uuid.uuid4().hex[:6]}"
    background_tasks.add_task(process_audit_log, admin_user["sub"], action_name, resource_id)

    # Invalidate cached report
    cache.invalidate("report:global_metrics")

    return {
        "message": f"Action '{action_name}' executed successfully by admin",
        "resource_id": resource_id,
    }
