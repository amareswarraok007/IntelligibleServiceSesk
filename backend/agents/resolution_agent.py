"""Resolution node using KB similarity lookup."""
from __future__ import annotations

from backend.agents.state import AgentState
from backend.services.kb_store import KBStore

KNOWN_AUTO = {
    "password": "Use self-service password reset portal, verify MFA, then retry login.",
    "vpn": "Restart VPN client, re-authenticate certificate, and reconnect via gateway 2.",
    "email": "Reconfigure IMAP/SMTP profile with org settings, then re-sync mailbox.",
}

kb = KBStore()


def run(state: AgentState) -> AgentState:
    query = f"{state.get('title', '')} {state.get('description', '')}"
    matches = kb.search(query, k=1)
    top = matches[0] if matches else None
    state["kb_article"] = top

    lowered = query.lower()
    auto_steps = None
    for key, steps in KNOWN_AUTO.items():
        if key in lowered:
            auto_steps = steps
            break

    if top and auto_steps and top["distance"] <= 0.45:
        state["status"] = "Resolved"
        state["resolved_steps"] = auto_steps
    else:
        state["status"] = "Open"

    state.setdefault("trace", []).append(
        {
            "agent": "resolution",
            "kb_title": top["title"] if top else None,
            "kb_distance": round(top["distance"], 4) if top else None,
            "auto_resolved": state.get("status") == "Resolved",
        }
    )
    return state
