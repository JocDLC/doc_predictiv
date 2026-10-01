"""Métricas locales de productividad sin datos de clientes."""

from __future__ import annotations

import json
from decimal import ROUND_HALF_UP, Decimal
from pathlib import Path
from statistics import median

# Orden fijo de las etapas del flujo automático para reportes comparables.
STAGE_ORDER = (
    "navigation",
    "comment_check",
    "field_read",
    "editor",
    "save_settle",
    "verification",
    "snapshot",
)


def round_elapsed_seconds(seconds: float) -> float:
    """Redondea una duración a una décima para reportes operativos."""
    return float(Decimal(str(max(0.0, float(seconds)))).quantize(Decimal("0.1"), rounding=ROUND_HALF_UP))


def metrics_path_for(results_path: Path) -> Path:
    """Ubica el resumen agregado junto al resultado de la cola."""
    return results_path.with_name(results_path.name.replace(".resultado.json", ".metricas.json"))


def summarize_results(results: list[dict], cycle_elapsed_seconds: float) -> dict:
    """Resume resultados sin preservar identificadores ni contenido de Leads."""
    saved_durations = [
        float(item["elapsed_seconds"])
        for item in results
        if item.get("status") == "guardado" and isinstance(item.get("elapsed_seconds"), (int, float))
    ]
    sample_size = len(results)
    saved = len(saved_durations)
    errors = sum(1 for item in results if item.get("status") == "error")
    duplicates = sum(1 for item in results if item.get("status") == "duplicado")
    already_documented = sum(1 for item in results if item.get("status") == "ya_documentado")
    partial = sum(1 for item in results if item.get("status") == "parcial")
    review = sum(1 for item in results if item.get("status") == "revision")
    stage_durations: dict[str, list[float]] = {}
    verify_reloads = 0
    for item in results:
        stages = item.get("stage_seconds")
        if isinstance(stages, dict):
            for stage, seconds in stages.items():
                if isinstance(seconds, (int, float)):
                    stage_durations.setdefault(stage, []).append(float(seconds))
        verify_reloads += int(item.get("verify_reloads") or 0)
    stage_seconds_mean = {
        stage: round_elapsed_seconds(sum(stage_durations[stage]) / len(stage_durations[stage]))
        for stage in STAGE_ORDER
        if stage_durations.get(stage)
    }
    summary = {
        "sample_size": sample_size,
        "saved": saved,
        "duplicates": duplicates,
        "errors": errors,
        "already_documented": already_documented,
        "partial": partial,
        "review": review,
        "success_rate": round((saved / sample_size * 100) if sample_size else 0.0, 1),
        "cycle_elapsed_seconds": round_elapsed_seconds(cycle_elapsed_seconds),
        "saved_elapsed_seconds": None,
        "stage_seconds_mean": stage_seconds_mean or None,
        "verify_reloads": verify_reloads,
        "time_thresholds": None,
        "effective_leads_per_hour": None,
    }
    if not saved:
        return summary

    summary["saved_elapsed_seconds"] = {
        "mean": round_elapsed_seconds(sum(saved_durations) / saved),
        "median": round_elapsed_seconds(median(saved_durations)),
        "min": round_elapsed_seconds(min(saved_durations)),
        "max": round_elapsed_seconds(max(saved_durations)),
    }
    summary["time_thresholds"] = {
        "normal_max": summary["saved_elapsed_seconds"]["mean"],
        "intermediate_max": round_elapsed_seconds(summary["saved_elapsed_seconds"]["mean"] * 1.2),
    }
    if cycle_elapsed_seconds > 0:
        summary["effective_leads_per_hour"] = round_elapsed_seconds(saved * 3600 / cycle_elapsed_seconds)
    return summary


def write_metrics(metrics_path: Path, summary: dict) -> None:
    """Persiste el resumen agregado localmente, sin resultados individuales."""
    metrics_path.write_text(json.dumps(summary, indent=2, ensure_ascii=False), encoding="utf-8")
