"""SQLite-backed report store."""

import json
import sqlite3
import uuid
from datetime import datetime
from pathlib import Path
from typing import Optional

from app.models.schemas import ObligationRow, PendingFormItem, PredictedQuery, RuleDecision, SalaryRow

DB_PATH = Path(__file__).resolve().parents[1] / "data" / "reports.db"


def _conn() -> sqlite3.Connection:
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS reports (
            report_id TEXT PRIMARY KEY,
            created_at TEXT NOT NULL,
            payload TEXT NOT NULL
        )
        """
    )
    conn.commit()
    return conn


def generate_report_id() -> str:
    return str(uuid.uuid4())


def save_report(
    report_id: str,
    eligibility: bool,
    decisions: list[RuleDecision],
    extracted_data: dict,
    salary_breakdown: list[SalaryRow],
    obligations: list[ObligationRow],
    missing_documents: list[str],
    pending_forms: list[PendingFormItem],
    predicted_queries: list[PredictedQuery],
    confidence_summary: dict,
    metadata: dict,
) -> None:
    payload = {
        "report_id": report_id,
        "created_at": datetime.utcnow().isoformat(),
        "eligibility": eligibility,
        "decisions": [d.model_dump() for d in decisions],
        "extracted_data": extracted_data,
        "salary_breakdown": [row.model_dump() for row in salary_breakdown],
        "obligations": [row.model_dump() for row in obligations],
        "missing_documents": missing_documents,
        "pending_forms": [item.model_dump() for item in pending_forms],
        "predicted_queries": [q.model_dump() for q in predicted_queries],
        "confidence_summary": confidence_summary,
        "metadata": metadata,
    }
    with _conn() as conn:
        conn.execute(
            "INSERT OR REPLACE INTO reports (report_id, created_at, payload) VALUES (?, ?, ?)",
            (report_id, payload["created_at"], json.dumps(payload)),
        )
        conn.commit()


def get_report(report_id: str) -> Optional[dict]:
    with _conn() as conn:
        cur = conn.execute("SELECT payload FROM reports WHERE report_id = ?", (report_id,))
        row = cur.fetchone()
    if not row:
        return None
    return json.loads(row[0])
