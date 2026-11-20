def test_health(client):
    r = client.get("/api/health").json()
    assert r["status"] == "ok" and r["kb_size"] >= 20


def test_validation_rejects_empty_body(client):
    assert client.post("/api/tickets", json={"subject": "x", "body": ""}).status_code == 422


def test_auto_resolved_ticket_is_fully_audited(client):
    r = client.post("/api/tickets", json={"subject": "Locked out", "body": "I forgot my password, please help me reset it."})
    assert r.status_code == 201
    t = r.json()
    assert t["status"] == "auto_resolved" and t["action"] == "password_reset"
    agents = [l["agent"] for l in t["logs"]]
    assert agents[:4] == ["triage", "retrieval", "resolution", "escalation"] and agents[-1] == "finalize"
    assert t["evidence"] and t["reply"] and t["decision_rule"]
    assert client.get(f"/api/tickets/{t['id']}").json()["id"] == t["id"]


def test_escalation_and_human_resolution_feeds_knowledge_base(client):
    t = client.post("/api/tickets", json={"subject": "Delete", "body": "Please delete my account and all my data."}).json()
    assert t["status"] == "escalated" and t["decision"] == "escalate"
    kb_before = client.get("/api/stats").json()["kb_size"]
    r = client.post(f"/api/tickets/{t['id']}/resolve", json={"resolution": "Privacy team verified identity and deleted the account within 48 hours.", "escalation_justified": True})
    assert r.status_code == 200 and r.json()["status"] == "resolved"
    assert client.get("/api/stats").json()["kb_size"] == kb_before + 1
    assert client.post(f"/api/tickets/{t['id']}/resolve", json={"resolution": "again please"}).status_code == 409


def test_resolved_knowledge_is_retrievable_for_next_ticket(client):
    t = client.post("/api/tickets", json={"subject": "Delete", "body": "How do I get my account deleted, who verifies my identity?"}).json()
    assert any(e["source"] == "resolution" or "delet" in e["content"].lower() for e in t["evidence"])


def test_stats_and_listing(client):
    s = client.get("/api/stats").json()
    assert s["total"] >= 3 and s["first_contact_resolution_rate"] is not None
    assert s["escalation_precision"] == 1.0 and {a["agent"] for a in s["agents"]} >= {"triage", "retrieval"}
    assert all(t["status"] == "escalated" for t in client.get("/api/tickets?status=escalated").json())


def test_unknown_ticket_404(client):
    assert client.get("/api/tickets/999999").status_code == 404


def test_feedback_loop_and_demo_seed(client):
    assert len(client.post("/api/demo/seed").json()["created"]) == 10
    r = client.post("/api/feedback/run").json()
    assert r["added"] >= 1
    assert client.post("/api/feedback/run").json()["added"] == 0  # idempotent
