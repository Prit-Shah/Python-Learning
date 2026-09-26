"""
03_dependency_injection_and_auth.py

============================================================
1. CONCEPT
============================================================

FastAPI features a first-class, hierarchical Dependency Injection (DI) system
that supersedes traditional untyped Express-style middleware with type-safe,
composable dependencies:

1. Declarative Dependency Injection (`Depends`):
   - Endpoints declare required resources as parameters: `user: User = Depends(get_current_user)`.
   - FastAPI inspects the parameter signature, executes the dependency callable,
     and injects the resolved return value directly into the handler.
   - Per-Request Caching (`use_cache=True`): If multiple sub-dependencies or routes
     require the same dependency within a single HTTP request, FastAPI runs it
     ONCE and shares the cached result across the entire request graph.

2. The Yield Dependency Pattern (Resource Lifecycle):
   - Defines setup and guaranteed teardown for scoped resources:
     ```python
     async def get_db_session():
         session = await SessionLocal()
         try:
             yield session
         finally:
             await session.close()
     ```
   - Teardown code after `yield` is guaranteed to execute even if an exception
     is raised inside the route handler.

3. Authentication & Role-Based Access Control (RBAC):
   - Credential Extraction: `HTTPBearer()` extracts Bearer tokens from the
     `Authorization: Bearer <token>` header.
   - User Resolution: `get_current_active_user` decodes the token and retrieves
     the user entity from state or database.
   - Parameterized RBAC Factories:
     ```python
     def require_role(role_name: str):
         def role_checker(user: User = Depends(get_current_active_user)):
             if role_name not in user.roles:
                 raise HTTPException(status_code=403, detail="Forbidden")
             return user
         return role_checker
     ```

4. Testing with `app.dependency_overrides`:
   - FastAPI allows replacing any dependency in the graph during unit tests:
     `app.dependency_overrides[get_current_active_user] = mock_user_provider`.
   - Completely decouples endpoints from external databases or auth providers
     during testing.


============================================================
2. JS / TS ANALOGY
============================================================

+------------------------------+------------------------------------+------------------------------------+
| Feature                      | Python (FastAPI)                   | JavaScript / TypeScript (Express)  |
+------------------------------+------------------------------------+------------------------------------+
| Cross-Cutting Logic          | Typed `Depends(fn)` injection      | Global `req, res, next` middleware |
| Injected Data Typing         | Strongly typed in handler signature| Untyped mutation (`req.user = ...`)|
| Resource Teardown            | `yield` dependency (`finally:`)    | `res.on('finish', ...)` listener   |
| Sub-dependency Composition   | Native DAG resolution              | Middleware ordering chains         |
| Per-Request Value Caching    | Built-in (`use_cache=True`)        | Manual attachment to `res.locals`  |
| Test Dependency Mocking      | `app.dependency_overrides[dep]`    | Mocking middleware / monkeypatching|
| RBAC Protection              | `Depends(require_role("admin"))`   | `authorize(["admin"])` middleware  |
+------------------------------+------------------------------------+------------------------------------+

Key JS vs Python Architecture Differences:
1. In Express, middleware functions mutate `req` (e.g. `req.user = user`), which
   loses type safety and introduces hidden dependencies between middleware ordering.
2. In FastAPI, dependencies return strongly-typed models injected explicitly
   into route handler parameters, providing instant IDE autocomplete and auto-generated
   OpenAPI security definitions.


============================================================
3. UNDER THE HOOD (CPython & Memory)
============================================================

1. The Dependency Graph DAG (Directed Acyclic Graph):
   - When FastAPI initializes an endpoint, it parses its parameters using
     Python's `inspect.signature()`.
   - It builds an internal dependency graph where nodes are dependency callables
     and edges represent sub-dependencies.
   - During request execution, FastAPI resolves the graph from leaves to root,
     evaluating each unique node once per request if caching is enabled.

2. Async Generator Mechanics in Yield Dependencies:
   - Yield dependencies are wrapped in `contextlib.asynccontextmanager` internally.
   - FastAPI enters the context before calling the endpoint handler and exits
     the context during response generation, ensuring deterministic teardown.


============================================================
4. COMMON GOTCHAS
============================================================

1. Swallowing Exceptions in Yield Dependencies:
   - Catching `except Exception: pass` inside a yield dependency swallows exceptions
     raised by the endpoint itself, making debugging impossible!
   - Always use `try...finally` without broad `except` blocks unless explicitly handling
     database transaction rollbacks.

2. Accidental Class Instantiation in Depends:
   - Writing `Depends(MyClass)` creates an instance of `MyClass` using its `__init__`.
   - Writing `Depends(MyClass())` executes `MyClass.__call__`.
   - Understand whether you want constructor injection or callable object execution.

3. Forgetting to Clear `app.dependency_overrides`:
   - Overriding a dependency in Test A without clearing `app.dependency_overrides = {}`
     causes Test A's mock to leak into Test B, Test C, and subsequent test suites.


============================================================
5. INTERVIEW READINESS (VERBAL SCRIPTS)
============================================================

Q1: "How does Dependency Injection in FastAPI differ from Express or NestJS middleware?"
Script:
"In Express, cross-cutting concerns like authentication or database access are implemented
via middleware functions that imperatively mutate a shared, untyped `req` object—such as
`req.user = user`. This creates implicit coupling and loses static type guarantees. In contrast,
FastAPI provides a formal, hierarchical Dependency Injection system using `Depends()`.
Dependencies are pure, strongly-typed callables that return structured objects injected directly
into handler arguments. This provides full IDE auto-completion, allows dependencies to depend
on other sub-dependencies in a Directed Acyclic Graph, and enables seamless unit testing
by overriding dependencies in test suites without patching."

Q2: "How does the yield dependency pattern manage resource lifecycles in FastAPI?"
Script:
"The `yield` dependency pattern provides deterministic setup and teardown for request-scoped
resources, such as database sessions or network transactions. The code before the `yield`
statement executes prior to the route handler, establishing the resource. The `yield` expression
injects the active resource into the endpoint. Finally, code in the `finally` block executes
after the HTTP response is generated, guaranteeing that database transactions are committed
or rolled back and connections are returned to the pool, even if the endpoint encountered an
unhandled exception."

Q3: "How do you implement scalable Role-Based Access Control (RBAC) in FastAPI?"
Script:
"We implement RBAC using higher-order factory dependencies. First, we create an authenticated
dependency like `get_current_user` that extracts the Bearer token, validates the JWT, and
resolves the user model. Then, we construct a factory function `require_role(required_role: str)`
that returns a callable dependency. This returned callable depends on `get_current_user`,
verifies that the user possesses the required permission, and raises an `HTTPException(403)`
if unauthorized. In routes, we simply apply `user = Depends(require_role('admin'))`,
achieving clean declarative security."
"""

import asyncio
from contextlib import asynccontextmanager
import sys
from fastapi import APIRouter, Depends, FastAPI, HTTPException, Security, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from pydantic import BaseModel
import httpx

# Ensure UTF-8 standard output across environments
if sys.stdout.encoding and sys.stdout.encoding.lower() != "utf-8":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass


# ============================================================
# MODELS & DOMAIN OBJECTS
# ============================================================

class User(BaseModel):
    user_id: int
    username: str
    email: str
    roles: list[str]


# Simulated user database
USER_DATABASE = {
    "token_alice": User(user_id=1, username="alice", email="alice@apex.internal", roles=["admin", "user"]),
    "token_bob": User(user_id=2, username="bob", email="bob@apex.internal", roles=["user"]),
}


# ============================================================
# DEPENDENCY INJECTION PIPELINE
# ============================================================

# 1. Bearer Token Extractor
security_scheme = HTTPBearer(auto_error=False)


# 2. Yield Dependency for Scoped Database Session Simulation
async def get_db_session():
    """Demonstrates yield dependency setup and guaranteed teardown."""
    session_id = "session_active"
    # Setup
    yield session_id
    # Teardown (guaranteed cleanup after response)
    session_id = "session_closed"


# 3. User Extraction Dependency
async def get_current_user(
    credentials: HTTPAuthorizationCredentials | None = Security(security_scheme),
) -> User:
    """Authenticates Bearer token and returns current User."""
    if credentials is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing Authorization Bearer header",
        )
    token = credentials.credentials
    user = USER_DATABASE.get(token)
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired token",
        )
    return user


# 4. Parameterized RBAC Dependency Factory
def require_role(required_role: str):
    """Factory generating role-checking dependencies."""
    def role_verifier(current_user: User = Depends(get_current_user)) -> User:
        if required_role not in current_user.roles:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"User does not possess required role: '{required_role}'",
            )
        return current_user
    return role_verifier


# ============================================================
# ROUTER CONFIGURATION
# ============================================================

auth_router = APIRouter(prefix="/api/v1/auth", tags=["auth"])


@auth_router.get("/me", response_model=User)
async def get_user_profile(user: User = Depends(get_current_user)):
    """Protected endpoint: accessible by any authenticated user."""
    return user


@auth_router.get("/admin/system-stats")
async def get_admin_dashboard(
    admin_user: User = Depends(require_role("admin")),
    db: str = Depends(get_db_session),
):
    """Restricted endpoint: strictly requires 'admin' role."""
    return {
        "status": "system_nominal",
        "authorized_by": admin_user.username,
        "db_session": db,
    }


# ============================================================
# APPLICATION
# ============================================================

app = FastAPI(title="Apex Security & RBAC Gateway")
app.include_router(auth_router)


def run_tests():
    async def main_suite():
        transport = httpx.ASGITransport(app=app)
        async with httpx.AsyncClient(transport=transport, base_url="http://testserver") as client:

            # ------------------------------------------------------------
            # Unauthenticated Request -> 401 Unauthorized
            # ------------------------------------------------------------
            unauth_resp = await client.get("/api/v1/auth/me")
            assert unauth_resp.status_code == 401
            assert "Missing Authorization" in unauth_resp.json()["detail"]

            # ------------------------------------------------------------
            # Invalid Token -> 401 Unauthorized
            # ------------------------------------------------------------
            bad_token_resp = await client.get(
                "/api/v1/auth/me",
                headers={"Authorization": "Bearer invalid_secret_token"},
            )
            assert bad_token_resp.status_code == 401
            assert "Invalid or expired token" in bad_token_resp.json()["detail"]

            # ------------------------------------------------------------
            # Authenticated User Profile (Alice) -> 200 OK
            # ------------------------------------------------------------
            alice_resp = await client.get(
                "/api/v1/auth/me",
                headers={"Authorization": "Bearer token_alice"},
            )
            assert alice_resp.status_code == 200
            assert alice_resp.json()["username"] == "alice"
            assert "admin" in alice_resp.json()["roles"]

            # ------------------------------------------------------------
            # RBAC Success: Alice is admin -> 200 OK
            # ------------------------------------------------------------
            admin_resp = await client.get(
                "/api/v1/auth/admin/system-stats",
                headers={"Authorization": "Bearer token_alice"},
            )
            assert admin_resp.status_code == 200
            assert admin_resp.json()["authorized_by"] == "alice"

            # ------------------------------------------------------------
            # RBAC Forbidden: Bob is only a regular user -> 403 Forbidden
            # ------------------------------------------------------------
            bob_forbidden_resp = await client.get(
                "/api/v1/auth/admin/system-stats",
                headers={"Authorization": "Bearer token_bob"},
            )
            assert bob_forbidden_resp.status_code == 403
            assert "required role: 'admin'" in bob_forbidden_resp.json()["detail"]

            # ------------------------------------------------------------
            # Testing Dependency Overrides in Unit Tests
            # ------------------------------------------------------------
            mock_test_user = User(
                user_id=999,
                username="mock_superadmin",
                email="mock@test.internal",
                roles=["admin"],
            )

            # Override get_current_user with mock provider
            app.dependency_overrides[get_current_user] = lambda: mock_test_user

            try:
                # Request with NO headers succeeds because dependency was overridden!
                override_resp = await client.get("/api/v1/auth/admin/system-stats")
                assert override_resp.status_code == 200
                assert override_resp.json()["authorized_by"] == "mock_superadmin"
            finally:
                # Always clear dependency overrides!
                app.dependency_overrides.clear()

    asyncio.run(main_suite())


if __name__ == "__main__":
    run_tests()
    print("03_dependency_injection_and_auth.py tests passed!")
