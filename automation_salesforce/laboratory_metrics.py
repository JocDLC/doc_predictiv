"""Métricas del laboratorio WhatsApp: comparación reproducible entre motores.

Se guarda por etapa y por lead, separando conexión inicial de sesión caliente.
El resumen agrega p50/p95 con una definición fija (método "nearest-rank") y
reporta cantidades por estado para comparar exactitud, no solo velocidad.
"""

from __future__ import annotations

import json
from pathlib import Path
from statistics import median

from productivity_metrics import round_elapsed_seconds

STAGE_ORDER = (
    "connect",
    "navigation",
    "eligibility_read",
    "button_check",
    "doc_prepare",
    "doc_save_verify",
    "send_click",
    "send_confirm",
    "total",
)


def percentile_nearest_rank(values: list[float], percentile: float) -> float | None:
    """pN por nearest-rank: el menor valor cuyo rango cubre N% de la muestra.

    Determinístico, sin interpolación; con muestras chicas p95 = máximo.
    """
    ordered = sorted(float(v) for v in values)
    if not ordered:
        return None
    rank = max(1, round(len(ordered) * percentile / 100 + 0.499999))
    return ordered[min(rank, len(ordered)) - 1]


def _duration_stats(durations: list[float]) -> dict | None:
    if not durations:
        return None
    return {
        "count": len(durations),
        "mean": round_elapsed_seconds(sum(durations) / len(durations)),
        "median": round_elapsed_seconds(median(durations)),
        "p95": round_elapsed_seconds(percentile_nearest_rank(durations, 95)),
        "min": round_elapsed_seconds(min(durations)),
        "max": round_elapsed_seconds(max(durations)),
    }


def summarize_laboratory_results(results: list[dict], cycle_elapsed_seconds: float = 0.0) -> dict:
    """Agrega resultados del laboratorio por motor.

    Cada entrada trae ``engine``, ``status``, ``elapsed_seconds`` y
    ``stage_seconds`` (dict por etapa). El resumen agrupa por motor y por
    modo para alimentar el informe comparativo.
    """
    by_engine: dict[str, list[dict]] = {}
    for item in results:
        engine = str(item.get("engine") or "desconocido")
        by_engine.setdefault(engine, []).append(item)

    engines = {}
    for engine, items in sorted(by_engine.items()):
        statuses: dict[str, int] = {}
        for item in items:
            status = str(item.get("status") or "error")
            statuses[status] = statuses.get(status, 0) + 1
        stage_durations: dict[str, list[float]] = {}
        totals: list[float] = []
        interventions = 0
        for item in items:
            if isinstance(item.get("elapsed_seconds"), (int, float)):
                totals.append(float(item["elapsed_seconds"]))
            for stage, seconds in (item.get("stage_seconds") or {}).items():
                if isinstance(seconds, (int, float)):
                    stage_durations.setdefault(stage, []).append(float(seconds))
            if item.get("intervencion_manual"):
                interventions += 1
        engines[engine] = {
            "sample_size": len(items),
            "statuses": statuses,
            "elapsed_seconds": _duration_stats(totals),
            "stage_seconds": {
                stage: _duration_stats(stage_durations[stage]) for stage in STAGE_ORDER if stage_durations.get(stage)
            },
            "manual_interventions": interventions,
        }
    summary = {
        "engines": engines,
        "total_leads": len(results),
        "unique_leads": len({str(item.get("lead_id") or "") for item in results}),
        "evaluations": len(results),
        "cycle_elapsed_seconds": round_elapsed_seconds(cycle_elapsed_seconds),
    }
    # Comparación pareada: leads evaluados por AMBOS motores en el mismo run
    # (modo comparación). Acuerdo por status y medianas del par apto.
    by_lead: dict[str, dict[str, dict]] = {}
    for item in results:
        lead_id = str(item.get("lead_id") or "")
        if lead_id:
            by_lead.setdefault(lead_id, {})[str(item.get("engine") or "")] = item
    pairs = [(lead_id, items) for lead_id, items in by_lead.items() if len(items) >= 2]
    if pairs:
        disagreements = []
        both_apto: dict[str, list[float]] = {}
        for lead_id, items in pairs:
            statuses = {str(item.get("status") or "") for item in items.values()}
            if len(statuses) > 1:
                disagreements.append({"lead_id": lead_id, "statuses": {e: i.get("status") for e, i in items.items()}})
            if statuses == {"apto"}:
                for engine, item in items.items():
                    if isinstance(item.get("elapsed_seconds"), (int, float)):
                        both_apto.setdefault(engine, []).append(float(item["elapsed_seconds"]))
        summary["paired"] = {
            "pairs": len(pairs),
            "agreements": len(pairs) - len(disagreements),
            "disagreements": disagreements,
            "both_apto_elapsed_median": {
                engine: round_elapsed_seconds(median(values)) for engine, values in sorted(both_apto.items())
            },
        }
    if cycle_elapsed_seconds > 0 and results:
        done = sum(
            count for engine in engines.values() for status, count in engine["statuses"].items() if status != "error"
        )
        summary["effective_leads_per_hour"] = round_elapsed_seconds(done * 3600 / cycle_elapsed_seconds)
    return summary


def write_metrics(metrics_path: Path, summary: dict) -> None:
    metrics_path.parent.mkdir(parents=True, exist_ok=True)
    metrics_path.write_text(json.dumps(summary, indent=2, ensure_ascii=False), encoding="utf-8")
