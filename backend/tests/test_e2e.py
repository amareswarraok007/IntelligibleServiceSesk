from fastapi.testclient import TestClient

from backend.main import app


VALID_CATEGORIES = {"Hardware", "Software", "Network", "Access", "Email", "SAP", "Other"}
VALID_PRIORITIES = {"Critical", "High", "Medium", "Low"}


def test_ticket_full_graph_flow() -> None:
    client = TestClient(app)

    create = client.post(
        "/tickets",
        json={"title": "Major outage in VPN", "description": "Corporate VPN outage across offices", "source": "web"},
    )
    assert create.status_code == 200
    ticket_id = create.json()["id"]

    proc = client.post(f"/process/{ticket_id}")
    assert proc.status_code == 200
    payload = proc.json()

    assert payload["status"] in ["Resolved", "Escalated"]
    assert payload["priority"] in VALID_PRIORITIES
    assert payload["category"] in VALID_CATEGORIES
    assert 0.0 <= payload["confidence"] <= 1.0
    assert isinstance(payload["trace_json"], list)
    assert any(step.get("agent") == "triage" for step in payload["trace_json"])


def test_metrics_shape() -> None:
    client = TestClient(app)
    response = client.get("/metrics")
    assert response.status_code == 200
    payload = response.json()

    assert set(payload.keys()) == {
        "total_tickets",
        "auto_resolved_rate",
        "escalation_rate",
        "avg_resolution_minutes",
        "routing_accuracy_proxy",
    }
