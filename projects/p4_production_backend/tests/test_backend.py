"""
Automated Pytest Suite for Project P4: Production Backend
"""
import pytest
import warnings
warnings.filterwarnings("ignore", category=DeprecationWarning)
from fastapi.testclient import TestClient
from ..app import app
from ..cache import cache
from ..tasks import audit_log_sink

client = TestClient(app)


def test_request_id_middleware():
    resp = client.get("/healthz")
    assert resp.status_code == 200
    assert "X-Request-ID" in resp.headers
    assert "X-Response-Time-Ms" in resp.headers


def test_auth_and_profile():
    # 1. Login user
    res_login = client.post("/api/v1/auth/login?username=alice&role=user")
    assert res_login.status_code == 200
    token = res_login.json()["access_token"]

    # 2. Access profile with token
    headers = {"Authorization": f"Bearer {token}"}
    res_prof = client.get("/api/v1/user/profile", headers=headers)
    assert res_prof.status_code == 200
    assert res_prof.json()["username"] == "alice"
    assert res_prof.json()["role"] == "user"


def test_role_based_access_control():
    # Regular user attempting admin action
    user_token = client.post("/api/v1/auth/login?username=bob&role=user").json()["access_token"]
    res_forbidden = client.post(
        "/api/v1/admin/action?action_name=purge_records",
        headers={"Authorization": f"Bearer {user_token}"},
    )
    assert res_forbidden.status_code == 403

    # Admin executing admin action
    admin_token = client.post("/api/v1/auth/login?username=root&role=admin").json()["access_token"]
    res_allowed = client.post(
        "/api/v1/admin/action?action_name=purge_records",
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert res_allowed.status_code == 200
    assert len(audit_log_sink) > 0


def test_cache_aside_lifecycle():
    token = client.post("/api/v1/auth/login?username=carol&role=user").json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    # Invalidate cache first
    cache.invalidate("report:global_metrics")

    # 1. First fetch -> Database/Fresh computation
    res1 = client.get("/api/v1/data/report", headers=headers)
    assert res1.status_code == 200
    assert res1.json()["source"] == "database"

    # 2. Second fetch -> Cache Hit
    res2 = client.get("/api/v1/data/report", headers=headers)
    assert res2.status_code == 200
    assert res2.json()["source"] == "cache"
