"""Diario transaccional del laboratorio WhatsApp (SQLite, biblioteca estándar).

La UI/web del navegador no ofrece garantías transaccionales, así que la
idempotencia del canal vive acá: cada ``operation_id`` (campaña+lead) pasa por
etapas persistentes y la reserva ``clic_reservado`` se COMMITEA antes de
invocar el envío. Si el proceso muere tras la reserva, el lead queda en
``send_status=indeterminado`` y jamás se reintenta automáticamente: la
ambigüedad es deliberada para no duplicar mensajes.

Datos locales del usuario: el archivo vive en ``ui_output/laboratorio/``,
directorio ignorado por git.
"""

from __future__ import annotations

import hashlib
import json
import sqlite3
from contextlib import closing
from datetime import datetime, timezone
from pathlib import Path

DB_FILE_NAME = "laboratorio.sqlite3"

STAGE_PENDIENTE = "pendiente"
STAGE_VERIFICADO = "verificado"
STAGE_DOC_PREPARADA = "documentacion_preparada"
STAGE_DOC_CONFIRMADA = "documentacion_confirmada"
STAGE_CLIC_RESERVADO = "clic_reservado"
STAGE_TERMINAL = "terminal"

# send_status
SEND_PENDIENTE = "pendiente"
SEND_CONFIRMADO = "confirmado"
SEND_NO_CONFIRMADO = "no_confirmado"
SEND_INDETERMINADO = "indeterminado"
SEND_BLOQUEADO = "bloqueado"

# Estados que impiden reprocesar el lead en la misma campaña.
BLOCKING_SEND_STATUS = (SEND_CONFIRMADO, SEND_NO_CONFIRMADO, SEND_INDETERMINADO)

_SCHEMA = """
CREATE TABLE IF NOT EXISTS campaigns (
    campaign_id TEXT PRIMARY KEY,
    created_at TEXT NOT NULL,
    source_file TEXT NOT NULL DEFAULT '',
    dataset_id TEXT NOT NULL DEFAULT ''
);
CREATE TABLE IF NOT EXISTS runs (
    run_id TEXT PRIMARY KEY,
    campaign_id TEXT NOT NULL,
    mode TEXT NOT NULL,
    engine TEXT NOT NULL,
    status TEXT NOT NULL,
    stop_requested INTEGER NOT NULL DEFAULT 0,
    requested_at TEXT NOT NULL,
    finished_at TEXT
);
CREATE TABLE IF NOT EXISTS operations (
    operation_id TEXT PRIMARY KEY,
    campaign_id TEXT NOT NULL,
    lead_id TEXT NOT NULL,
    engine TEXT NOT NULL,
    next_int INTEGER,
    attempt_line TEXT,
    history_sha TEXT,
    stage TEXT NOT NULL,
    doc_status TEXT NOT NULL DEFAULT 'pendiente',
    send_status TEXT NOT NULL DEFAULT 'pendiente',
    review_reason TEXT NOT NULL DEFAULT '',
    evidence TEXT NOT NULL DEFAULT '{}',
    updated_at TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_operations_campaign ON operations (campaign_id, lead_id);
CREATE INDEX IF NOT EXISTS idx_operations_lead ON operations (lead_id);
CREATE TABLE IF NOT EXISTS send_reservations (
    org_source TEXT NOT NULL,
    lead_id TEXT NOT NULL,
    channel TEXT NOT NULL,
    state TEXT NOT NULL,
    campaign_id TEXT NOT NULL DEFAULT '',
    operation_id TEXT NOT NULL DEFAULT '',
    reserved_at TEXT NOT NULL,
    PRIMARY KEY (org_source, lead_id, channel)
);
"""


def _now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def history_fingerprint(existing_comment: object) -> str:
    """Huella del historial leído antes de componer (diagnóstico, no privacidad:
    el hash no permite reconstruir el texto)."""
    return hashlib.sha256(str(existing_comment or "").encode("utf-8")).hexdigest()[:16]


def operation_id(campaign_id: str, lead_id: str) -> str:
    return f"{campaign_id}|{lead_id}"


class LaboratoryStore:
    """Acceso al diario; una conexión por operación (el runner es único).

    ``org_source`` identifica la instalación Salesforce (host de
    ``salesforce_url``): las reservas de envío se clavan por
    ``(org_source, lead_id, channel)`` y bloquean el reenvío entre campañas
    e importaciones nuevas del mismo lead.
    """

    def __init__(self, path: Path, org_source: str = "", channel: str = "whatsapp"):
        self.path = Path(path)
        self.org_source = str(org_source or "")
        self.channel = str(channel or "whatsapp")
        self.path.parent.mkdir(parents=True, exist_ok=True)
        with closing(sqlite3.connect(self.path)) as conn:
            conn.row_factory = sqlite3.Row
            conn.executescript(_SCHEMA)
            self._migrate_reservations(conn)
            conn.commit()

    def _migrate_reservations(self, conn: sqlite3.Connection) -> None:
        """Bloqueo conservador de operaciones históricas con envío resuelto
        o ambiguo: una reserva previa en otra campaña sigue impidiendo el
        reenvío aunque el archivo de importación cambie."""
        rows = conn.execute(
            "SELECT operation_id, campaign_id, lead_id, stage, send_status FROM operations"
            " WHERE send_status IN ('confirmado', 'no_confirmado', 'indeterminado')"
            "    OR stage = 'clic_reservado'"
        ).fetchall()
        for row in rows:
            state = row["send_status"] if row["send_status"] != "pendiente" else SEND_INDETERMINADO
            conn.execute(
                "INSERT OR IGNORE INTO send_reservations"
                " (org_source, lead_id, channel, state, campaign_id, operation_id, reserved_at)"
                " VALUES (?, ?, ?, ?, ?, ?, ?)",
                (
                    self.org_source,
                    row["lead_id"],
                    self.channel,
                    state,
                    row["campaign_id"],
                    row["operation_id"],
                    _now(),
                ),
            )

    def _connect(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self.path)
        conn.row_factory = sqlite3.Row
        return conn

    # --- campañas y runs ---------------------------------------------------

    def ensure_campaign(self, campaign_id: str, source_file: str = "", dataset_id: str = "") -> None:
        with closing(self._connect()) as conn:
            conn.execute(
                "INSERT OR IGNORE INTO campaigns (campaign_id, created_at, source_file, dataset_id)"
                " VALUES (?, ?, ?, ?)",
                (campaign_id, _now(), source_file, dataset_id),
            )
            conn.commit()

    def register_run(self, run_id: str, campaign_id: str, mode: str, engine: str) -> None:
        with closing(self._connect()) as conn:
            conn.execute(
                "INSERT OR REPLACE INTO runs (run_id, campaign_id, mode, engine, status, requested_at)"
                " VALUES (?, ?, ?, ?, 'en_curso', ?)",
                (run_id, campaign_id, mode, engine, _now()),
            )
            conn.commit()

    def finish_run(self, run_id: str, status: str) -> None:
        with closing(self._connect()) as conn:
            conn.execute(
                "UPDATE runs SET status = ?, finished_at = ? WHERE run_id = ?",
                (status, _now(), run_id),
            )
            conn.commit()

    def request_stop(self, run_id: str) -> bool:
        with closing(self._connect()) as conn:
            cursor = conn.execute(
                "UPDATE runs SET stop_requested = 1 WHERE run_id = ? AND status = 'en_curso'",
                (run_id,),
            )
            conn.commit()
            return cursor.rowcount > 0

    def stop_requested(self, run_id: str) -> bool:
        with closing(self._connect()) as conn:
            row = conn.execute("SELECT stop_requested FROM runs WHERE run_id = ?", (run_id,)).fetchone()
            return bool(row and row["stop_requested"])

    def run_info(self, run_id: str) -> dict | None:
        with closing(self._connect()) as conn:
            row = conn.execute("SELECT * FROM runs WHERE run_id = ?", (run_id,)).fetchone()
            return dict(row) if row else None

    def latest_run(self) -> dict | None:
        with closing(self._connect()) as conn:
            row = conn.execute("SELECT * FROM runs ORDER BY requested_at DESC, run_id DESC LIMIT 1").fetchone()
            return dict(row) if row else None

    def active_run(self) -> dict | None:
        with closing(self._connect()) as conn:
            row = conn.execute("SELECT * FROM runs WHERE status = 'en_curso' LIMIT 1").fetchone()
            return dict(row) if row else None

    def recent_runs(self, limit: int = 20) -> list[dict]:
        with closing(self._connect()) as conn:
            rows = conn.execute(
                "SELECT run_id, campaign_id, mode, engine, status, requested_at, finished_at"
                " FROM runs ORDER BY requested_at DESC, run_id DESC LIMIT ?",
                (int(limit),),
            ).fetchall()
            return [dict(row) for row in rows]

    # --- operaciones por lead ----------------------------------------------

    def begin_operation(
        self,
        campaign_id: str,
        lead_id: str,
        engine: str,
        next_int: int | None = None,
        attempt_line: str = "",
        existing_comment: str = "",
    ) -> dict:
        """Crea (o devuelve) la operación del lead en la campaña.

        Si ya existe con texto previsto, se conserva la MISMA línea de intento:
        la reanudación nunca recalcula N ni la hora.
        """
        op_id = operation_id(campaign_id, lead_id)
        with closing(self._connect()) as conn:
            conn.execute(
                "INSERT OR IGNORE INTO operations"
                " (operation_id, campaign_id, lead_id, engine, next_int, attempt_line, history_sha,"
                "  stage, updated_at) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
                (
                    op_id,
                    campaign_id,
                    lead_id,
                    engine,
                    next_int,
                    attempt_line,
                    history_fingerprint(existing_comment) if existing_comment else None,
                    STAGE_PENDIENTE,
                    _now(),
                ),
            )
            if attempt_line:
                conn.execute(
                    "UPDATE operations SET engine = ?, next_int = COALESCE(next_int, ?),"
                    " attempt_line = COALESCE(attempt_line, ?),"
                    " history_sha = COALESCE(history_sha, ?), updated_at = ?"
                    " WHERE operation_id = ? AND stage = ?",
                    (
                        engine,
                        next_int,
                        attempt_line,
                        history_fingerprint(existing_comment),
                        _now(),
                        op_id,
                        STAGE_PENDIENTE,
                    ),
                )
            conn.commit()
            row = conn.execute("SELECT * FROM operations WHERE operation_id = ?", (op_id,)).fetchone()
            return dict(row)

    def advance(
        self,
        campaign_id: str,
        lead_id: str,
        stage: str,
        *,
        doc_status: str | None = None,
        send_status: str | None = None,
        review_reason: str | None = None,
        evidence: dict | None = None,
    ) -> None:
        """Avanza la etapa y opcionalmente los ejes doc/send."""
        sets = ["stage = ?", "updated_at = ?"]
        params: list = [stage, _now()]
        if doc_status is not None:
            sets.append("doc_status = ?")
            params.append(doc_status)
        if send_status is not None:
            sets.append("send_status = ?")
            params.append(send_status)
        if review_reason is not None:
            sets.append("review_reason = ?")
            params.append(review_reason)
        if evidence is not None:
            sets.append("evidence = ?")
            params.append(json.dumps(evidence, ensure_ascii=False))
        params.append(operation_id(campaign_id, lead_id))
        with closing(self._connect()) as conn:
            conn.execute(f"UPDATE operations SET {', '.join(sets)} WHERE operation_id = ?", params)
            if stage == STAGE_TERMINAL and send_status:
                conn.execute(
                    "UPDATE send_reservations SET state = ? WHERE org_source = ? AND lead_id = ? AND channel = ?",
                    (send_status, self.org_source, lead_id, self.channel),
                )
            conn.commit()

    def get_operation(self, campaign_id: str, lead_id: str) -> dict | None:
        with closing(self._connect()) as conn:
            row = conn.execute(
                "SELECT * FROM operations WHERE operation_id = ?",
                (operation_id(campaign_id, lead_id),),
            ).fetchone()
            return dict(row) if row else None

    def reservation_for(self, lead_id: str) -> dict | None:
        """Reserva de envío del lead en este origen/canal (cualquier campaña)."""
        with closing(self._connect()) as conn:
            row = conn.execute(
                "SELECT * FROM send_reservations WHERE org_source = ? AND lead_id = ? AND channel = ?",
                (self.org_source, lead_id, self.channel),
            ).fetchone()
            return dict(row) if row else None

    def is_blocked(self, campaign_id: str, lead_id: str) -> tuple[bool, str]:
        """True si la operación ya es terminal o quedó con envío ambiguo,
        o si existe una reserva de envío previa en CUALQUIER campaña del
        mismo origen (importaciones nuevas no eluden el bloqueo)."""
        reservation = self.reservation_for(lead_id)
        if reservation:
            return True, f"reserva:{reservation['state']}"
        operation = self.get_operation(campaign_id, lead_id)
        if not operation:
            return False, ""
        if operation["send_status"] in BLOCKING_SEND_STATUS:
            return True, str(operation["send_status"])
        if operation["stage"] in (STAGE_CLIC_RESERVADO,):
            return True, SEND_INDETERMINADO
        if operation["stage"] == STAGE_TERMINAL:
            return True, f"terminal:{operation['send_status']}"
        return False, ""

    def reserve_send_click(self, campaign_id: str, lead_id: str) -> None:
        """Etapa ``clic_reservado`` + reserva de envío en UNA transacción.

        Se COMMITEA antes del clic real: si el proceso muere después, ambas
        señales quedan persistidas y el lead jamás se reintenta.
        """
        with closing(self._connect()) as conn:
            conn.execute(
                "UPDATE operations SET stage = ?, updated_at = ? WHERE operation_id = ?",
                (STAGE_CLIC_RESERVADO, _now(), operation_id(campaign_id, lead_id)),
            )
            conn.execute(
                "INSERT OR IGNORE INTO send_reservations"
                " (org_source, lead_id, channel, state, campaign_id, operation_id, reserved_at)"
                " VALUES (?, ?, ?, ?, ?, ?, ?)",
                (
                    self.org_source,
                    lead_id,
                    self.channel,
                    "reservado",
                    campaign_id,
                    operation_id(campaign_id, lead_id),
                    _now(),
                ),
            )
            conn.commit()

    def update_reservation_state(self, lead_id: str, state: str) -> None:
        with closing(self._connect()) as conn:
            conn.execute(
                "UPDATE send_reservations SET state = ? WHERE org_source = ? AND lead_id = ? AND channel = ?",
                (state, self.org_source, lead_id, self.channel),
            )
            conn.commit()

    def latest_operation_for_lead(self, lead_id: str) -> dict | None:
        """Última operación del lead en cualquier campaña (para auditoría)."""
        with closing(self._connect()) as conn:
            row = conn.execute(
                "SELECT * FROM operations WHERE lead_id = ? ORDER BY updated_at DESC LIMIT 1",
                (lead_id,),
            ).fetchone()
            return dict(row) if row else None

    def update_plan(
        self,
        campaign_id: str,
        lead_id: str,
        next_int: int,
        attempt_line: str,
        existing_comment: str,
    ) -> None:
        """Actualiza el texto previsto si el historial cambió antes del Save.

        Solo aplica a etapas tempranas: una vez reservado el clic la línea ya
        está (o no) escrita y no se renumera.
        """
        with closing(self._connect()) as conn:
            conn.execute(
                "UPDATE operations SET next_int = ?, attempt_line = ?, history_sha = ?,"
                " updated_at = ? WHERE operation_id = ? AND stage IN (?, ?)",
                (
                    next_int,
                    attempt_line,
                    history_fingerprint(existing_comment),
                    _now(),
                    operation_id(campaign_id, lead_id),
                    STAGE_PENDIENTE,
                    STAGE_VERIFICADO,
                ),
            )
            conn.commit()

    def pending_for_campaign(self, campaign_id: str) -> list[dict]:
        with closing(self._connect()) as conn:
            rows = conn.execute(
                "SELECT * FROM operations WHERE campaign_id = ? AND stage != ? ORDER BY lead_id",
                (campaign_id, STAGE_TERMINAL),
            ).fetchall()
            return [dict(row) for row in rows]

    def counts_for_campaign(self, campaign_id: str) -> dict:
        with closing(self._connect()) as conn:
            rows = conn.execute(
                "SELECT doc_status, send_status, stage, COUNT(*) AS n FROM operations"
                " WHERE campaign_id = ? GROUP BY doc_status, send_status, stage",
                (campaign_id,),
            ).fetchall()
            return [dict(row) for row in rows]


def store_path_for(ui_output_directory: Path) -> Path:
    return Path(ui_output_directory) / "laboratorio" / DB_FILE_NAME
