"""
Phase 7: Backend with FastAPI - Dependency Injection & Authentication
================================================================================
1. CONCEPT & JS/TS ANALOGY:
   - Dependency Injection ('Depends()') is FastAPI's most powerful architectural feature.
   - Core Concepts:
     * Declarative Dependencies: Functions passed to 'Depends(get_db)' are executed automatically
       before the route handler runs.
     * Hierarchical Sub-Dependencies: Dependencies can themselves depend on other dependencies!
     * The Yield Dependency Pattern:
       def get_db():
           db = create_session()
           try:
               yield db # Handed to route handler
           finally:
               db.close() # Cleaned up guaranteed after response is generated!
     * Request Caching: By default ('use_cache=True'), if multiple dependencies or routes request
       the same dependency in a single HTTP request, it runs ONCE and the result is reused.
     * Authentication & Security:
       - Header token extraction via 'HTTPBearer()' or 'OAuth2PasswordBearer()'.
       - Token verification and User extraction.
       - Role-Based Access Control (RBAC): Factory dependency 'require_role("admin")'.
   - JS/TS Analogy:
     * Express uses middleware: 'app.use((req, res, next) => { req.user = user; next(); })'.
       Downside: 'req.user' is untyped and mutated globally.
     * FastAPI uses Dependency Injection: Dependencies return strongly typed objects injected
       directly into route handler arguments with full IDE auto-completion!

2. UNDER THE HOOD (CPython & Memory):
   - FastAPI builds a Directed Acyclic Graph (DAG) of all dependencies for each endpoint upon startup.
   - When a request arrives, it resolves the DAG efficiently, caching intermediate values per request.

3. COMMON GOTCHA:
   - Swallowing exceptions inside a yield dependency:
     def get_db():
         try: yield db
         except Exception: pass # BUG: Suppresses errors that occurred in the route handler!

4. 🎙️ INTERVIEW READINESS: VERBAL RESPONSE SCRIPT
   -----------------------------------------------------------------------------
   Q: "How does Dependency Injection work in FastAPI, how does it differ from Express
       middleware, and how do you implement authentication and RBAC with Depends()?"
   
   HOW TO ANSWER OUT LOUD (60-90 sec script):
   1. Dependency Injection vs Express Middleware:
      "In Express, cross-cutting concerns like auth or DB sessions are handled via middleware
       functions that mutate the global 'req' object ('req.user = user'). This is loosely typed
       and difficult to trace.
       FastAPI uses a formal, hierarchical Dependency Injection system with 'Depends()'.
       Dependencies are pure, strongly-typed Python functions that resolve into explicit function
       parameters, giving us type-safety, automatic Swagger docs, and simple unit testing via dependency overrides."
   2. The Yield Dependency Pattern:
      "For stateful resources like database connections, we use yield dependencies: setup runs
       before the endpoint, the resource is yielded, and teardown (like closing a transaction)
       is guaranteed to execute after the response finishes."
   3. Auth & RBAC Architecture:
      "We implement authentication by chaining dependencies:
       First, an OAuth2/Bearer dependency extracts the JWT token from the Authorization header.
       Second, a 'get_current_user' dependency decodes the token and fetches the user entity.
       Third, a parameterized factory dependency—like 'require_role('admin')'—verifies the user's
       permissions before allowing execution to proceed, raising an HTTP 403 Forbidden if unauthorized."
================================================================================
"""

import sys
import warnings
warnings.filterwarnings('ignore', category=DeprecationWarning)
from typing import Annotated, Dict
from fastapi import FastAPI, Depends, HTTPException, status, Header
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from fastapi.testclient import TestClient
from pydantic import BaseModel

# Ensure UTF-8 output encoding across Windows terminals
if sys.stdout.encoding and sys.stdout.encoding.lower() != 'utf-8':
    try:
        sys.stdout.reconfigure(encoding='utf-8')
    except Exception:
        pass


app = FastAPI(title="Dependency Injection & Auth Demo")

# Simulated User Database
FAKE_USERS_DB = {
    "token_alice": {"username": "alice", "role": "admin"},
    "token_bob": {"username": "bob", "role": "user"},
}

security = HTTPBearer(auto_error=False)


# ==============================================================================
# DEPENDENCY HIERARCHY
# ==============================================================================

# 1. Base Dependency: Extract & Authenticate Current User
async def get_current_user(credentials: Annotated[HTTPAuthorizationCredentials, Depends(security)]):
    """Decodes bearer token and returns authenticated user."""
    if not credentials or not credentials.credentials:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing or invalid authentication token."
        )
    
    token = credentials.credentials
    user = FAKE_USERS_DB.get(token)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired token."
        )
    return user


# 2. Parameterized Dependency Factory: Role-Based Access Control (RBAC)
def require_role(required_role: str):
    """Returns a dependency verifying the authenticated user possesses the required role."""
    async def role_checker(current_user: Annotated[dict, Depends(get_current_user)]):
        if current_user["role"] != required_role:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Access forbidden: requires '{required_role}' role."
            )
        return current_user
    return role_checker


# ==============================================================================
# ROUTE DEFINITIONS USING DEPENDENCY INJECTION
# ==============================================================================

@app.get("/me")
async def read_my_profile(current_user: Annotated[dict, Depends(get_current_user)]):
    """Requires valid authentication."""
    return {"message": f"Hello, {current_user['username']}!", "role": current_user["role"]}


@app.get("/admin/metrics")
async def read_admin_metrics(admin_user: Annotated[dict, Depends(require_role("admin"))]):
    """Strictly restricted to users with 'admin' role."""
    return {
        "metrics": "SYSTEM_OPTIMAL",
        "cpu_load": "12%",
        "active_users": 1420,
        "authorized_by": admin_user["username"]
    }


# ==============================================================================
# SELF-TEST CHALLENGES (Using FastAPI TestClient)
# ==============================================================================

def run_tests():
    print("\n[*] Running automated tests for 03_dependency_injection_and_auth.py...")
    with TestClient(app) as client:
        # 1. Unauthenticated request -> 401
        res = client.get("/me")
        assert res.status_code == 401
        assert "missing or invalid" in res.json()["detail"].lower()

        # 2. Authenticated user (Bob - 'user' role)
        headers_bob = {"Authorization": "Bearer token_bob"}
        res = client.get("/me", headers=headers_bob)
        assert res.status_code == 200
        assert res.json()["role"] == "user"

        # 3. Bob attempts to access admin endpoint -> 403 Forbidden
        res = client.get("/admin/metrics", headers=headers_bob)
        assert res.status_code == 403
        assert "forbidden" in res.json()["detail"].lower()

        # 4. Authenticated admin (Alice - 'admin' role) accessing admin endpoint -> 200 OK
        headers_alice = {"Authorization": "Bearer token_alice"}
        res = client.get("/admin/metrics", headers=headers_alice)
        assert res.status_code == 200
        assert res.json()["metrics"] == "SYSTEM_OPTIMAL"
        assert res.json()["authorized_by"] == "alice"

    print("[SUCCESS] All Dependency Injection & Auth tests passed cleanly!")


if __name__ == "__main__":
    print("=" * 65)
    print("Execution: Phase 7 - Dependency Injection & RBAC Auth")
    print("=" * 65)
    run_tests()
    print("=" * 65)
