"""Triage node for category/priority extraction with Gemini-compatible fallback."""
from __future__ import annotations

import json
import os
import re
from typing import Any, Literal

import requests
from pydantic import BaseModel, Field, ValidationError

from backend.agents.state import AgentState

CATEGORIES = ["Hardware", "Software", "Network", "Access", "Email", "SAP", "Other"]
PRIORITIES = ["Critical", "High", "Medium", "Low"]


class TriageOutput(BaseModel):
    """Strict triage response schema."""

    category: Literal["Hardware", "Software", "Network", "Access", "Email", "SAP", "Other"]
    priority: Literal["Critical", "High", "Medium", "Low"]
    confidence: float = Field(ge=0.0, le=1.0)
    reasoning: str = Field(min_length=1, max_length=200)


class GeminiLikeClient:
    def __init__(self) -> None:
        self.api_key = os.getenv("GEMINI_API_KEY")
        self.model = os.getenv("GEMINI_MODEL", "gemini-1.5-flash")

    def classify(self, text: str) -> dict[str, Any]:
        if not self.api_key:
            return self._fallback(text)
        prompt = (
            "Return strict JSON with keys: category, priority, confidence, reasoning. "
            f"category in {CATEGORIES}; priority in {PRIORITIES}; confidence in [0,1].\nIssue: {text}"
        )
        url = f"https://generativelanguage.googleapis.com/v1beta/models/{self.model}:generateContent?key={self.api_key}"
        payload = {"contents": [{"parts": [{"text": prompt}]}]}
        try:
            resp = requests.post(url, json=payload, timeout=8)
            resp.raise_for_status()
            content = resp.json()["candidates"][0]["content"]["parts"][0]["text"]
            parsed = self._extract_json(content)
            return self._validate(parsed)
        except Exception:
            return self._fallback(text)

    def _extract_json(self, content: str) -> dict[str, Any]:
        try:
            return json.loads(content)
        except json.JSONDecodeError:
            match = re.search(r"\{.*\}", content, flags=re.DOTALL)
            if not match:
                raise
            return json.loads(match.group(0))

    def _validate(self, parsed: dict[str, Any]) -> dict[str, Any]:
        try:
            validated = TriageOutput.model_validate(parsed)
            return validated.model_dump()
        except ValidationError:
            raise ValueError("Invalid triage JSON schema")

    def _fallback(self, text: str) -> dict[str, Any]:
        lower = text.lower()
        rules = [
            ("outage", "Network", "Critical", 0.95, "Outage indicates critical impact"),
            ("password", "Access", "High", 0.93, "Password/access issue detected"),
            ("vpn", "Network", "High", 0.88, "VPN/network issue detected"),
            ("sap", "SAP", "High", 0.90, "SAP keyword detected"),
            ("email", "Email", "Medium", 0.86, "Email issue keyword detected"),
            ("laptop", "Hardware", "Medium", 0.82, "Hardware device keyword detected"),
            ("install", "Software", "Medium", 0.78, "Software install/config issue"),
        ]
        for key, c, p, conf, reason in rules:
            if key in lower:
                return TriageOutput(category=c, priority=p, confidence=conf, reasoning=reason).model_dump()
        return TriageOutput(
            category="Other", priority="Low", confidence=0.6, reasoning="No strong keyword; defaulted"
        ).model_dump()


client = GeminiLikeClient()


def run(state: AgentState) -> AgentState:
    merged = f"{state.get('title', '')}\n{state.get('description', '')}"
    triage = client.classify(merged)
    state.update(triage)
    state.setdefault("trace", []).append({"agent": "triage", **triage})
    return state
