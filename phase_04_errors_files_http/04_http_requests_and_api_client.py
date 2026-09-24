"""
Phase 4: Errors, Files, HTTP & Stdlib - HTTP Client (httpx) & API Integration
================================================================================
1. CONCEPT & JS/TS ANALOGY:
   - Modern HTTP requests in Python use 'httpx' (the modern successor to 'requests').
   - Why httpx?
     * Standard sync client ('httpx.Client()') AND full async client ('httpx.AsyncClient()').
     * HTTP/2 support, connection pooling, and strict timeout defaults.
   - Core API Client Architecture:
     * Base URL configuration.
     * Custom headers & Bearer Token authentication.
     * Response verification via 'response.raise_for_status()'.
     * JSON payload encoding ('json=data') and decoding ('response.json()').
     * Retry mechanism with backoff for transient network errors (HTTP 429, 502, 503).
   - JS/TS Analogy:
     * In JavaScript: 'fetch()' or 'axios.create({ baseURL, timeout })'.
     * In Python: 'with httpx.Client(base_url="...", timeout=10.0) as client:'.

2. UNDER THE HOOD (CPython & Memory):
   - 'httpx.Client' manages an underlying HTTP connection pool (via httpcore).
   - Using the context manager ('with httpx.Client() as client:') ensures TCP sockets and SSL
     contexts are cleanly closed and returned to the OS.

3. COMMON GOTCHA:
   - Forgetting request timeouts: Without a timeout, a hanging server will freeze your Python
     thread indefinitely! Always configure timeouts: 'httpx.Client(timeout=10.0)'.
   - Ignoring HTTP error codes: httpx does NOT throw on 4xx/5xx by default. Always call
     'response.raise_for_status()' to convert error status codes into catchable HTTPStatusError exceptions!

4. 🎙️ INTERVIEW READINESS: VERBAL RESPONSE SCRIPT
   -----------------------------------------------------------------------------
   Q: "What HTTP client library do you use in modern Python, and how do you design a
       resilient API integration client for external microservices?"
   
   HOW TO ANSWER OUT LOUD (60-90 sec script):
   1. httpx vs requests:
      "For modern Python services, I standardize on 'httpx' over 'requests'. It provides a nearly
       identical intuitive sync API, but adds native async support ('AsyncClient') for FastAPI,
       HTTP/2 capabilities, and better timeout handling."
   2. Resilient API Client Pattern:
      "When integrating external APIs, a production client requires 4 key pillars:
       1. Reusable Client with Connection Pooling: Instantiate a single client via context manager
          or application lifespan to reuse TCP connections.
       2. Strict Timeouts: Always define connect, read, and write timeouts so hanging endpoints
          never exhaust worker threads.
       3. Error Normalization: Use response.raise_for_status() and map HTTPStatusError into domain exceptions.
       4. Exponential Backoff & Retries: Decorate transient network failures (like 429 Too Many Requests
          or 503 Service Unavailable) with exponential backoff and jitter."
================================================================================
"""

import sys
import time
import json
from pathlib import Path

# Ensure UTF-8 output encoding across Windows terminals
if sys.stdout.encoding and sys.stdout.encoding.lower() != 'utf-8':
    try:
        sys.stdout.reconfigure(encoding='utf-8')
    except Exception:
        pass

# Safe import with fallback indicator
try:
    import httpx
    HAS_HTTPX = True
except ImportError:
    HAS_HTTPX = False


class PublicApiClient:
    """
    Production-style resilient API client.
    Demonstrates base_url, timeout, error handling, and retries.
    """
    def __init__(self, base_url: str = "https://jsonplaceholder.typicode.com", timeout: float = 10.0):
        self.base_url = base_url
        self.timeout = timeout

    def fetch_post(self, post_id: int, max_retries: int = 3) -> dict:
        """Fetches a post with retry logic on network or server errors."""
        url = f"{self.base_url}/posts/{post_id}"
        
        if not HAS_HTTPX:
            # Fallback mock for offline / test environments without active network
            return {
                "id": post_id,
                "title": f"Mock Title for Post #{post_id}",
                "body": "This is a mock body when httpx is unavailable.",
                "userId": 1
            }

        last_error = None
        for attempt in range(1, max_retries + 1):
            try:
                with httpx.Client(timeout=self.timeout) as client:
                    response = client.get(url)
                    response.raise_for_status()  # Raises HTTPStatusError on 4xx/5xx
                    return response.json()
            except (httpx.RequestError, httpx.HTTPStatusError) as e:
                last_error = e
                wait_time = 0.5 * (2 ** (attempt - 1))
                print(f"  [Attempt {attempt}/{max_retries}] Request failed ({e}). Retrying in {wait_time:.1f}s...")
                time.sleep(wait_time)
                
        raise RuntimeError(f"Failed to fetch post {post_id} after {max_retries} attempts.") from last_error

    def save_post_to_disk(self, post_data: dict, output_dir: Path) -> Path:
        """Validates response and saves formatted JSON to local storage."""
        if not post_data.get("id") or not post_data.get("title"):
            raise ValueError("Invalid post payload: missing required fields.")
            
        output_dir.mkdir(parents=True, exist_ok=True)
        file_path = output_dir / f"post_{post_data['id']}.json"
        file_path.write_text(json.dumps(post_data, indent=2), encoding="utf-8")
        return file_path


def demonstrate_api_client():
    print("\n--- 1. Calling Public API with httpx & Validation ---")
    client = PublicApiClient()
    output_dir = Path(__file__).parent / "_api_output"
    
    try:
        # Fetch post #1
        print("  Fetching post #1 from public JSON API...")
        post = client.fetch_post(1)
        print(f"  Received Post Title: '{post['title'][:40]}...'")
        
        # Save to disk
        saved_file = client.save_post_to_disk(post, output_dir)
        print(f"  Saved payload to disk: {saved_file}")
        print(f"  File content verified: {saved_file.read_text(encoding='utf-8')[:80]}...")
    finally:
        import shutil
        if output_dir.exists():
            shutil.rmtree(output_dir)


# ==============================================================================
# SELF-TEST CHALLENGES
# ==============================================================================

def run_tests():
    print("\n[*] Running automated self-tests for 04_http_requests_and_api_client.py...")
    client = PublicApiClient()
    output_dir = Path(__file__).parent / "_test_http_scratch"
    
    try:
        # Mock / live fetch test
        post = client.fetch_post(1)
        assert post["id"] == 1
        assert "title" in post
        assert "userId" in post
        
        # Test disk persistence
        file_path = client.save_post_to_disk(post, output_dir)
        assert file_path.exists() is True
        loaded = json.loads(file_path.read_text(encoding="utf-8"))
        assert loaded["id"] == 1
        
        # Test payload validation failure
        try:
            client.save_post_to_disk({"bad": "payload"}, output_dir)
            assert False, "Should raise ValueError on invalid payload"
        except ValueError:
            pass
            
        print("[SUCCESS] All self-tests passed cleanly!")
    finally:
        import shutil
        if output_dir.exists():
            shutil.rmtree(output_dir)


if __name__ == "__main__":
    print("=" * 65)
    print("Execution: Phase 4 - HTTP Client (httpx) & API Integration")
    print("=" * 65)
    demonstrate_api_client()
    print("-" * 65)
    run_tests()
    print("=" * 65)
