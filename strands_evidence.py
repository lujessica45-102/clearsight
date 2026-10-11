"""Strands hook: automatically records every tool call the agent makes,
then saves the whole record to the Closure Call evidence vault on Akamai."""
import os
from datetime import datetime, timezone
import requests
from strands.hooks import HookProvider, HookRegistry, AfterToolCallEvent

EVIDENCE_URL = os.environ.get("EVIDENCE_URL", "http://172.236.108.63/evidence")
EVIDENCE_TOKEN = os.environ.get("EVIDENCE_TOKEN", "")

class EvidenceRecorder(HookProvider):
    def __init__(self, facility_id: str):
        self.facility_id = facility_id
        self.tool_calls = []

    def register_hooks(self, registry: HookRegistry, **kwargs):
        registry.add_callback(AfterToolCallEvent, self._record)

    def _record(self, event: AfterToolCallEvent):
        self.tool_calls.append({
            "time": datetime.now(timezone.utc).isoformat(),
            "tool": event.tool_use.get("name"),
            "input": event.tool_use.get("input"),
            "result": event.result,
        })

    def save(self, recommendation: dict) -> str:
        """Call once after the agent finishes. Returns the evidence_id."""
        record = {"inputs_seen_by_agent": self.tool_calls, "recommendation": recommendation}
        r = requests.post(EVIDENCE_URL, headers={"X-Evidence-Token": EVIDENCE_TOKEN},
                          json={"facility_id": self.facility_id, "record": record}, timeout=20)
        r.raise_for_status()
        return r.json()["evidence_id"]