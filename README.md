# Smart Helpdesk Ticketing MVP (SIH 25195)

Single vertical slice using FastAPI + LangGraph + SQLite + ChromaDB.

## Features implemented
- Unified ingestion from web form and mocked GLPI JSON endpoint.
- NLP triage (category, priority, confidence, reasoning) via Gemini-compatible wrapper with deterministic fallback.
- Intelligent routing based on team skills + historical routing scores.
- Auto-resolution using KB similarity lookup (RAG-like local vector memory via ChromaDB).
- Escalation when ticket is Critical or SLA has <20% remaining.
- Alert notifier logs SMS/email events to console and DB.
- Agent trace visible in UI ticket detail panel.
- Judge-friendly `/metrics` endpoint with outcome and routing proxies.

## Setup
```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
```

## Run
```bash
python backend/seed.py
uvicorn backend.main:app --reload
```
Open: http://127.0.0.1:8000

## 4-step Demo script for judges
1. **Load baseline**  
   Run seed and verify `GET /metrics` returns zeros/initial rates with `total_tickets` populated.
2. **Show unified ingestion**  
   Create one ticket from UI (`/`) and one from mocked GLPI (`POST /ingest/glpi-mock`).
3. **Show autonomous processing**  
   Trigger `POST /process/{ticket_id}` and inspect: triage fields, assigned team, and full `trace_json` in ticket detail panel.
4. **Show outcomes and governance**  
   Demonstrate one auto-resolved known issue (password/vpn/email) and one critical/escalated issue, then open `/metrics` to show:
   - `auto_resolved_rate`
   - `escalation_rate`
   - `avg_resolution_minutes`
   - `routing_accuracy_proxy`

## API curl examples
```bash
curl -X POST http://127.0.0.1:8000/tickets \
  -H 'Content-Type: application/json' \
  -d '{"title":"Password reset failed","description":"Cannot login after reset","source":"web"}'

curl -X POST http://127.0.0.1:8000/ingest/glpi-mock \
  -H 'Content-Type: application/json' \
  -d '{"name":"Email sync issue","content":"Outlook not syncing for sales user","requester":"user@org.com"}'

curl -X POST http://127.0.0.1:8000/process/1
curl http://127.0.0.1:8000/tickets
curl http://127.0.0.1:8000/tickets/1
curl http://127.0.0.1:8000/metrics
```

## `/metrics` response shape
```json
{
  "total_tickets": 22,
  "auto_resolved_rate": 0.273,
  "escalation_rate": 0.182,
  "avg_resolution_minutes": 7.45,
  "routing_accuracy_proxy": 0.818
}
```

## What is mocked vs real
- **Mocked:** Gemini LLM when API key missing (deterministic rules), GLPI endpoint input, notifier delivery (console + DB only).
- **Real/local:** FastAPI APIs, LangGraph orchestration, SQLite persistence, ChromaDB vector search, end-to-end flow and UI.
