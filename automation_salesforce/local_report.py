from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path

from report_reader import VisibleLead


def report_payload(visible_row_count: int, leads: list[VisibleLead]) -> dict:
    return {
        "visible_row_count": visible_row_count,
        "leads": [
            {
                "lead_id": lead.lead_id,
                "created_at": lead.created_at,
                "grid_position": lead.grid_position,
                "status": lead.status,
                **({"details": lead.details} if lead.details else {}),
            }
            for lead in leads
        ],
    }


def available_report_path(output_directory: Path, generated_at: datetime) -> Path:
    stem = f"leads_sin_gestion_{generated_at:%Y%m%d_%H%M%S}"
    candidate = output_directory / f"{stem}.json"
    suffix = 1
    while candidate.exists():
        candidate = output_directory / f"{stem}_{suffix}.json"
        suffix += 1
    return candidate


def write_unassigned_leads_report(
    visible_row_count: int,
    leads: list[VisibleLead],
    output_directory: Path,
    generated_at: datetime | None = None,
) -> Path:
    output_directory.mkdir(parents=True, exist_ok=True)
    timestamp = generated_at or datetime.now()
    report_path = available_report_path(output_directory, timestamp)
    report_path.write_text(
        json.dumps(report_payload(visible_row_count, leads), ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    return report_path
