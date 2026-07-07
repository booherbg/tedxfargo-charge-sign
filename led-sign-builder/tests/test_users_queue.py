import pytest
from fastapi.testclient import TestClient

from signforge.web.app import create_app

TINY = {
    "name": "t",
    "content": {"text": "I", "cap_height_mm": 40},
    "style": {"kind": "channel", "backer": "none"},
    "leds": {"kind": "none"},
    "texture": {"mode": "none"},
}


@pytest.fixture
def stack(tmp_path, monkeypatch):
    monkeypatch.setenv("SIGNFORGE_ADMIN_PASSWORD", "admin-secret-1")
    app = create_app(open_mode=False, db_path=str(tmp_path / "db.sqlite"),
                     workdir=str(tmp_path / "work"), workers=0)   # workers=0: jobs stay queued
    return app, TestClient(app)


def _login(client, email, pw):
    r = client.post("/api/auth/login", json={"email": email, "password": pw})
    assert r.status_code == 200
    return client


def test_auth_flow_and_me(stack):
    app, client = stack
    assert client.post("/api/build", json={"params": TINY}).status_code == 401

    r = client.post("/api/auth/register", json={"email": "bob@x.com", "password": "hunter2222"})
    assert r.status_code == 200 and r.json()["user"]["tier"] == "free"
    me = client.get("/api/auth/me").json()
    assert me["user"]["email"] == "bob@x.com"
    assert me["limits"]["max_cap_mm"] == 150.0

    client.post("/api/auth/logout")
    assert client.get("/api/auth/me").json()["user"] is None

    assert client.post(
        "/api/auth/login", json={"email": "bob@x.com", "password": "wrong-pass"}
    ).status_code == 401


def test_free_tier_size_and_queue_caps(stack):
    app, client = stack
    client.post("/api/auth/register", json={"email": "f@x.com", "password": "password99"})

    big = dict(TINY, content={"text": "I", "cap_height_mm": 400})
    r = client.post("/api/build", json={"params": big})
    assert r.status_code == 403 and "premium" in r.text

    assert client.post("/api/build", json={"params": TINY}).status_code == 200
    r = client.post("/api/build", json={"params": TINY})       # 1 queued already
    assert r.status_code == 429 and "queued" in r.text


def test_admin_promotes_and_priority_ordering(stack):
    app, client = stack
    client.post("/api/auth/register", json={"email": "free@x.com", "password": "password99"})
    fr = client.post("/api/build", json={"params": TINY})
    assert fr.status_code == 200
    free_job = fr.json()["job"]

    admin = TestClient(app)
    _login(admin, "admin@local", "admin-secret-1")
    users = admin.get("/api/admin/users").json()["users"]
    target = next(u for u in users if u["email"] == "free@x.com")

    pr = admin.post("/api/build", json={"params": TINY})       # admin = premium priority
    assert pr.status_code == 200
    prem_job = pr.json()["job"]

    q = app.state.queue
    assert q.position(prem_job) == 1                            # jumps the free job
    assert q.position(free_job) == 2

    admin.post(f"/api/admin/users/{target['id']}", json={"tier": "premium"})
    assert admin.get("/api/auth/me").json()["user"]["role"] == "admin"
    users2 = admin.get("/api/admin/users").json()["users"]
    assert next(u for u in users2 if u["id"] == target["id"])["tier"] == "premium"

    # non-admin cannot see admin endpoints or foreign jobs
    assert client.get("/api/admin/users").status_code == 403
    assert client.get(f"/api/jobs/{prem_job}").status_code == 403


def test_cancel_queued_job(stack):
    app, client = stack
    client.post("/api/auth/register", json={"email": "c@x.com", "password": "password99"})
    job = client.post("/api/build", json={"params": TINY}).json()["job"]
    r = client.delete(f"/api/jobs/{job}")
    assert r.status_code == 200 and r.json()["cancelled"]
    assert client.get(f"/api/jobs/{job}").json()["status"] == "cancelled"


def test_delete_and_clear_finished(tmp_path):
    import time

    from signforge.web.app import create_app

    app = create_app(open_mode=True, db_path=str(tmp_path / "d.sqlite"),
                     workdir=str(tmp_path / "w"), workers=1)
    client = TestClient(app)
    job = client.post("/api/build", json={"params": TINY}).json()["job"]
    for _ in range(120):
        if client.get(f"/api/jobs/{job}").json()["status"] == "done":
            break
        time.sleep(0.2)
    outdir = app.state.queue.jobs[job]["outdir"]
    from pathlib import Path

    assert Path(outdir).exists()
    r = client.delete(f"/api/jobs/{job}")
    assert r.status_code == 200 and r.json().get("deleted")
    assert not Path(outdir).exists()                      # files gone
    assert client.get(f"/api/jobs/{job}").status_code == 404
    assert all(j["id"] != job for j in client.get("/api/jobs").json()["jobs"])

    j2 = client.post("/api/build", json={"params": TINY}).json()["job"]
    for _ in range(120):
        if client.get(f"/api/jobs/{j2}").json()["status"] == "done":
            break
        time.sleep(0.2)
    r = client.post("/api/jobs/clear")
    assert r.json()["cleared"] >= 1
    assert client.get("/api/jobs").json()["jobs"] == []


def test_daily_quota(stack, monkeypatch):
    app, client = stack
    client.post("/api/auth/register", json={"email": "q@x.com", "password": "password99"})
    store = app.state.store
    uid = next(u for u in store.list_users() if u["email"] == "q@x.com")["id"]
    for _ in range(6):
        store.record_build(uid)
    r = client.post("/api/build", json={"params": TINY})
    assert r.status_code == 429 and "quota" in r.text
