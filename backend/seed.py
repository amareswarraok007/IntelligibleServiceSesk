"""Seed script for Smart Helpdesk MVP."""
from __future__ import annotations

from datetime import datetime, timedelta
import sys
from pathlib import Path

if __package__ is None or __package__ == "":
    sys.path.append(str(Path(__file__).resolve().parents[1]))

from backend.db import Base, db_context, engine
from backend.models import RoutingScore, Team, Ticket
from backend.services.kb_store import KBStore

KB_DOCS = [
    {"id": 1, "title": "Password Reset Guide", "content": "Reset password via SSO portal and complete MFA verification.", "tags": ["password", "access"]},
    {"id": 2, "title": "VPN Reconnect", "content": "Troubleshoot VPN disconnect by restarting client and renewing certificate.", "tags": ["vpn", "network"]},
    {"id": 3, "title": "Email Client Setup", "content": "Configure SMTP/IMAP server and apply app password for email client.", "tags": ["email", "config"]},
    {"id": 4, "title": "Laptop Overheating", "content": "Clean vents, update BIOS, and run hardware diagnostics.", "tags": ["hardware"]},
    {"id": 5, "title": "SAP Login Error", "content": "Check SAP role mapping and reset secure token.", "tags": ["sap", "access"]},
    {"id": 6, "title": "WiFi Issue", "content": "Forget network profile and reconnect with enterprise credentials.", "tags": ["network"]},
    {"id": 7, "title": "Blue Screen Fix", "content": "Collect minidump and update graphics driver.", "tags": ["hardware", "software"]},
    {"id": 8, "title": "Printer Offline", "content": "Re-add printer queue and restart print spooler.", "tags": ["hardware"]},
    {"id": 9, "title": "Software Install", "content": "Use company portal for approved software installation.", "tags": ["software"]},
    {"id": 10, "title": "Outlook Sync Delay", "content": "Repair OST file and clear cached mode issues.", "tags": ["email"]},
    {"id": 11, "title": "Firewall Block", "content": "Whitelist application in endpoint firewall policy.", "tags": ["network", "software"]},
    {"id": 12, "title": "Account Unlock", "content": "Unlock AD account and force password change.", "tags": ["access"]},
    {"id": 13, "title": "Database Timeout", "content": "Check network latency and increase DB client timeout.", "tags": ["network", "software"]},
    {"id": 14, "title": "Teams Mic Issue", "content": "Update audio driver and set default microphone permissions.", "tags": ["software"]},
    {"id": 15, "title": "Remote Desktop Access", "content": "Enable RDP permissions and verify VPN route.", "tags": ["access", "network"]},
]


def main() -> None:
    Base.metadata.create_all(bind=engine)
    with db_context() as db:
        db.query(RoutingScore).delete()
        db.query(Ticket).delete()
        db.query(Team).delete()

        teams = [
            Team(name="Network Ops", skills=["Network", "Access"]),
            Team(name="Endpoint Support", skills=["Hardware", "Software"]),
            Team(name="Identity & Access", skills=["Access", "Email"]),
            Team(name="SAP Basis", skills=["SAP", "Access"]),
            Team(name="Messaging Team", skills=["Email", "Software"]),
            Team(name="Service Desk", skills=["Other", "Software"]),
        ]
        db.add_all(teams)
        db.flush()

        score_map = {
            "Network": {"Network Ops": 0.9, "Service Desk": 0.4},
            "Hardware": {"Endpoint Support": 0.88, "Service Desk": 0.45},
            "Software": {"Endpoint Support": 0.7, "Messaging Team": 0.65, "Service Desk": 0.55},
            "Access": {"Identity & Access": 0.85, "Network Ops": 0.5},
            "Email": {"Messaging Team": 0.9, "Identity & Access": 0.55},
            "SAP": {"SAP Basis": 0.95},
            "Other": {"Service Desk": 0.8},
        }
        name_to_id = {t.name: t.id for t in teams}
        for cat, items in score_map.items():
            for team_name, score in items.items():
                db.add(RoutingScore(category=cat, team_id=name_to_id[team_name], score=score))

        samples = [
            ("Cannot reset password", "My password reset link fails", "web"),
            ("VPN disconnects", "VPN drops every 10 minutes", "glpi"),
            ("Laptop heating", "Dell laptop overheating", "web"),
            ("Email sync fail", "Outlook not syncing", "web"),
            ("SAP auth issue", "SAP login token invalid", "glpi"),
        ]
        for i in range(20):
            s = samples[i % len(samples)]
            db.add(
                Ticket(
                    title=f"{s[0]} #{i+1}",
                    description=s[1],
                    source=s[2],
                    status="New",
                    sla_deadline=datetime.utcnow() + timedelta(hours=4 + (i % 5)),
                    trace_json=[{"agent": "seed", "action": "generated"}],
                )
            )

    KBStore().add_documents(KB_DOCS)
    print("Seed complete: teams, routing scores, 20 tickets, 15 KB docs")


if __name__ == "__main__":
    main()
