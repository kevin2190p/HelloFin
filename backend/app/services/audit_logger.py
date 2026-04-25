"""
Audit Logger – SOC2-Ready Structured Logging
"""
import json, time, os
from pathlib import Path
import structlog

logger = structlog.get_logger("fakeout.audit")
LOG_DIR = Path("logs")
LOG_DIR.mkdir(exist_ok=True)


class AuditLogger:
    """JSON audit logger for SOC2 compliance. Logs all API events to file."""

    def __init__(self):
        self.log_file = LOG_DIR / "audit.jsonl"

    def log_event(self, event_type: str, **kwargs):
        entry = {"timestamp": time.time(), "event": event_type, **kwargs}
        with open(self.log_file, "a") as f:
            f.write(json.dumps(entry) + "\n")
        logger.info("audit_event", event=event_type)

    def log_risk_assessment(self, txn_id, score, level, factors):
        self.log_event("risk_assessment", txn_id=txn_id, score=score,
                       level=level, factor_count=len(factors))

    def log_transaction_action(self, txn_id, action, actor="system"):
        self.log_event("transaction_action", txn_id=txn_id,
                       action=action, actor=actor)
