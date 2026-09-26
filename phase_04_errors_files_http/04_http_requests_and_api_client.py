"""
04_http_requests_and_api_client.py

============================================================
1. CONCEPT
============================================================

Interacting with external HTTP services in modern Python is centered on `httpx`,
connection pooling, strict timeouts, error normalization, and resilient retry
mechanisms:

1. Modern HTTP Client Landscape: `httpx` vs `requests`:
   - `requests`: The historic standard for synchronous Python HTTP requests.
     Lacks native `async/await` capabilities and HTTP/2.
   - `httpx`: The modern next-generation HTTP library. Features a nearly identical
     intuitive API to `requests`, while providing:
     - Native Synchronous Client: `httpx.Client()`.
     - Native Asynchronous Client: `httpx.AsyncClient()` for FastAPI and asyncio.
     - HTTP/2 support, connection pooling, and strict default timeouts.
     - Built-in Mock Transport (`httpx.MockTransport`) for offline testing.

2. Connection Pooling & Context Managers:
   - Creating a client via `with httpx.Client(base_url="...") as client:` creates
     an underlying HTTP connection pool (via `httpcore`).
   - Reuses TCP connections across requests, drastically reducing TLS handshake
     latency in high-throughput microservices.
   - Context manager guarantees cleanup of sockets and SSL contexts.

3. Request Lifecycle & Payload Handling:
   - Query Parameters: `params={"page": 1, "filter": "active"}`.
   - JSON Payloads: `json={"name": "Alice"}` (auto-serializes and sets `Content-Type: application/json`).
   - Headers & Auth: `headers={"Authorization": f"Bearer {token}"}`.
   - Response Extraction: `response.status_code`, `response.text`, `response.json()`.

4. Status Code Handling & `raise_for_status()`:
   - By default, `httpx` does NOT raise an exception on 4xx or 5xx responses!
   - Calling `response.raise_for_status()` raises `httpx.HTTPStatusError` on errors.
   - Production clients normalize HTTP errors into application domain exceptions.

5. Resilient API Client Pattern:
   - Strict Timeouts: Always configure connect, read, and write timeouts (`httpx.Timeout(10.0, connect=5.0)`).
   - Transient Retry Strategy: Retrying on idempotent requests encountering 429
     (Too Many Requests), 502 (Bad Gateway), 503 (Service Unavailable), or timeouts,
     using exponential backoff.


============================================================
2. JS / TS ANALOGY
============================================================

+------------------------------+------------------------------------+------------------------------------+
| Feature                      | Python                             | JavaScript / TypeScript (Node.js)  |
+------------------------------+------------------------------------+------------------------------------+
| HTTP Client Instance         | `with httpx.Client(...) as client:`| `axios.create({ baseURL, ... })`   |
| Native Async Client          | `httpx.AsyncClient()`              | `fetch()` / `axios`                |
| Base URL Configuration       | `httpx.Client(base_url="...")`     | `axios.create({ baseURL: "..." })` |
| JSON Body Serializer         | `client.post(url, json=data)`      | `axios.post(url, data)`            |
| Status Code Check            | `response.raise_for_status()`      | Check `response.ok` / axios default|
| Custom Headers / Auth        | `headers={"Authorization": ...}`   | `headers: { Authorization: ... }`  |
| Connection Pool Teardown     | Guaranteed by `client.close()`     | Keep-alive agent destruction       |
| In-Memory Mocking            | `httpx.MockTransport(handler)`     | `msw` (Mock Service Worker) / nock |
+------------------------------+------------------------------------+------------------------------------+

Key JS vs Python HTTP Client Differences:
1. In JS `fetch()`, 404 or 500 responses do NOT reject the promise—you must
   manually check `response.ok`. Similarly in `httpx`, requests succeed unless you
   call `response.raise_for_status()`, which converts error responses into
   catchable `HTTPStatusError` exceptions.
2. In Python, `httpx` has built-in in-memory transport mocking (`httpx.MockTransport`),
   enabling unit tests to simulate HTTP servers with zero network or socket overhead.


============================================================
3. UNDER THE HOOD (CPython & Memory)
============================================================

1. The HTTP Connection Pool (`httpcore`):
   - `httpx.Client` delegates low-level networking to `httpcore`.
   - Maintains a pool of reusable TCP socket connections.
   - When a request completes, the connection is returned to the pool rather than
     closed with a TCP `FIN` packet, saving ~100ms of TLS negotiation per request.

2. Bytecode & Network Thread Safety:
   - Network I/O operations in CPython (e.g. `socket.connect`, `socket.recv`)
     release the Global Interpreter Lock (GIL).
   - Multiple threads making concurrent HTTP requests can execute I/O in parallel
     without blocking each other.

3. MockTransport Mechanics:
   - `httpx.MockTransport` accepts a handler function `(request: httpx.Request) -> httpx.Response`.
   - Completely bypasses OS sockets, providing 100% deterministic, instant unit testing.


============================================================
4. COMMON GOTCHAS
============================================================

1. Omitting Request Timeouts:
   - `httpx.get("https://api.example.com")`
   - Default timeout is 5.0 seconds in `httpx` (unlike `requests` which has NO default timeout!).
   - In production, always configure explicit timeouts per operation.

2. Forgetting `response.raise_for_status()`:
   - If an endpoint returns 500 Internal Server Error, execution continues
     silently into `response.json()`, which might fail with a confusing `JSONDecodeError`.

3. Instantiating a New Client Per Request:
   - Anti-pattern: `httpx.get(...)` inside a loop or request handler.
   - Creates a new TCP connection and TLS handshake on EVERY invocation.
   - Solution: Create a single `httpx.Client()` session and reuse it.

4. Reading Response Content Multiple Times in Streams:
   - In streaming responses (`client.stream()`), the payload is consumed lazily.
   - Calling `response.read()` or iterating `response.iter_bytes()` exhausts the stream.


============================================================
5. INTERVIEW READINESS (VERBAL SCRIPTS)
============================================================

Q1: "Why is httpx preferred over requests in modern Python services?"
Script:
"`httpx` is the modern successor to `requests`. While it maintains the familiar,
intuitive synchronous API of `requests`, it introduces three crucial architectural
advantages: first, native asynchronous support via `httpx.AsyncClient`, which is essential
for non-blocking I/O in modern async frameworks like FastAPI; second, HTTP/2 support
for multiplexing requests over a single connection; and third, built-in in-memory mocking
via `httpx.MockTransport`, allowing deterministic unit testing without external mocking
libraries or network socket setup."

Q2: "How do you design a production-grade HTTP API client for microservice communication?"
Script:
"A resilient production HTTP client requires five architectural safeguards:
First, connection pooling via a shared `httpx.Client` wrapped in an application lifespan
context manager to reuse TCP and TLS handshakes. Second, strict, segmented timeouts
defining limits for connect, read, and write phases to prevent hanging threads. Third,
error normalization: invoking `response.raise_for_status()` and translating low-level
`HTTPStatusError` codes into typed domain exceptions like `EntityNotFoundError` or
`AuthenticationError`. Fourth, retry logic with exponential backoff and jitter for
idempotent operations encountering transient 429 or 503 errors. Finally, structured logging
to emit request IDs, latency metrics, and HTTP status codes for distributed observability."

Q3: "How does httpx.MockTransport work, and how does it benefit test suites?"
Script:
"`httpx.MockTransport` is a native transport adapter in `httpx` that intercepts HTTP
requests in-memory and routes them to a custom handler function that returns an
`httpx.Response`. Because it operates entirely in Python memory without touching the
OS network stack, sockets, or loopback interfaces, tests run orders of magnitude faster
and remain completely isolated from network flakiness. It allows test suites to easily
simulate network latency, HTTP 500 error responses, rate-limiting headers, and payload
structures deterministically."
"""

import sys
import httpx

# Ensure UTF-8 standard output across environments
if sys.stdout.encoding and sys.stdout.encoding.lower() != "utf-8":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass


# ============================================================
# DOMAIN API EXCEPTIONS
# ============================================================

class ApiClientError(Exception):
    """Base exception for external API communication failures."""
    pass


class ResourceNotFoundError(ApiClientError):
    """Raised on HTTP 404."""
    pass


class RateLimitExceededError(ApiClientError):
    """Raised on HTTP 429."""
    pass


# ============================================================
# PRODUCTION RESILIENT API CLIENT
# ============================================================

class UserManagementClient:
    """Production-grade API client with pooling, timeouts, and error normalization."""

    def __init__(self, base_url: str, api_token: str, transport: httpx.BaseTransport | None = None):
        self._client = httpx.Client(
            base_url=base_url,
            headers={
                "Authorization": f"Bearer {api_token}",
                "Content-Type": "application/json",
                "User-Agent": "ApexUserService/2.0",
            },
            timeout=httpx.Timeout(timeout=10.0, connect=3.0),
            transport=transport,
        )

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self._client.close()

    def get_user(self, user_id: int) -> dict:
        """Fetch user by ID with error normalization."""
        try:
            response = self._client.get(f"/api/v1/users/{user_id}")
            response.raise_for_status()
            return response.json()
        except httpx.HTTPStatusError as err:
            if err.response.status_code == 404:
                raise ResourceNotFoundError(f"User {user_id} not found") from err
            elif err.response.status_code == 429:
                raise RateLimitExceededError("Rate limit exceeded") from err
            raise ApiClientError(f"HTTP request failed: {err.response.status_code}") from err
        except httpx.RequestError as err:
            raise ApiClientError(f"Network transport error: {err}") from err

    def create_user(self, user_data: dict) -> dict:
        """Create new user resource."""
        try:
            response = self._client.post("/api/v1/users", json=user_data)
            response.raise_for_status()
            return response.json()
        except httpx.HTTPStatusError as err:
            raise ApiClientError(f"Failed to create user: {err.response.status_code}") from err


def run_tests():
    # ============================================================
    # 1. IN-MEMORY TESTING VIA httpx.MockTransport
    # ============================================================

    # Define mock handler simulating server responses without opening sockets
    def mock_handler(request: httpx.Request) -> httpx.Response:
        url_path = request.url.path
        auth_header = request.headers.get("Authorization", "")

        # Verify bearer token was sent
        if auth_header != "Bearer sec_token_123":
            return httpx.Response(401, json={"error": "Unauthorized"})

        # Route: GET /api/v1/users/1 -> Success
        if request.method == "GET" and url_path == "/api/v1/users/1":
            return httpx.Response(200, json={"id": 1, "username": "alice", "active": True})

        # Route: GET /api/v1/users/404 -> Not Found
        if request.method == "GET" and url_path == "/api/v1/users/404":
            return httpx.Response(404, json={"error": "Not Found"})

        # Route: GET /api/v1/users/429 -> Rate Limited
        if request.method == "GET" and url_path == "/api/v1/users/429":
            return httpx.Response(429, json={"error": "Rate limit exceeded"})

        # Route: POST /api/v1/users -> Created
        if request.method == "POST" and url_path == "/api/v1/users":
            return httpx.Response(201, json={"id": 2, "username": "bob", "status": "created"})

        return httpx.Response(500, json={"error": "Unhandled route"})

    mock_transport = httpx.MockTransport(mock_handler)


    # ============================================================
    # 2. CLIENT INITIALIZATION & CONTEXT MANAGER
    # ============================================================

    with UserManagementClient(
        base_url="https://internal.api.net",
        api_token="sec_token_123",
        transport=mock_transport,
    ) as client:

        # ------------------------------------------------------------
        # Successful GET Request
        # ------------------------------------------------------------
        user = client.get_user(1)
        assert user["id"] == 1
        assert user["username"] == "alice"
        assert user["active"] is True

        # ------------------------------------------------------------
        # Error Normalization: HTTP 404 -> ResourceNotFoundError
        # ------------------------------------------------------------
        caught_404 = False
        try:
            client.get_user(404)
        except ResourceNotFoundError as err:
            caught_404 = True
            assert "User 404 not found" in str(err)
            assert isinstance(err.__cause__, httpx.HTTPStatusError)
        assert caught_404 is True

        # ------------------------------------------------------------
        # Error Normalization: HTTP 429 -> RateLimitExceededError
        # ------------------------------------------------------------
        caught_429 = False
        try:
            client.get_user(429)
        except RateLimitExceededError:
            caught_429 = True
        assert caught_429 is True

        # ------------------------------------------------------------
        # Successful POST with JSON body
        # ------------------------------------------------------------
        new_user = client.create_user({"username": "bob", "role": "admin"})
        assert new_user["id"] == 2
        assert new_user["username"] == "bob"
        assert new_user["status"] == "created"


    # ============================================================
    # 3. DIRECT RAW httpx CLIENT CAPABILITIES
    # ============================================================

    # Testing raw client query params and header handling
    with httpx.Client(transport=mock_transport, base_url="https://test.net") as raw_client:
        resp = raw_client.get(
            "/api/v1/users/1",
            headers={"Authorization": "Bearer sec_token_123"},
            params={"expand": "profile"},
        )
        assert resp.status_code == 200
        assert resp.is_success is True
        assert resp.headers["content-type"] == "application/json"


if __name__ == "__main__":
    run_tests()
    print("04_http_requests_and_api_client.py tests passed!")
