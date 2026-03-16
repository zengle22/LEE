"""Async audit logger with SQLite and NDJSON dual-write storage."""

from __future__ import annotations

import asyncio
import json
from pathlib import Path
from typing import List, Optional

import aiosqlite

from .audit_schemas import AuditQuery
from .error_codes import QAEntryErrorCode
from .schemas import AuditEntry, AuditAction, EntrySource, ExecutionPath, ExecutionStatus, SSOTAxisBinding


class AuditLogger:
    """Persist QA execution audit entries to SQLite and NDJSON."""

    def __init__(
        self,
        db_path: Optional[Path] = None,
        archive_path: Optional[Path] = None,
    ) -> None:
        self.db_path = Path(db_path or Path("data") / "audit" / "audit_log.db")
        self.archive_path = Path(archive_path or Path("data") / "audit" / "audit_log.ndjson")
        self._queue: "asyncio.Queue[Optional[AuditEntry]]" = asyncio.Queue()
        self._worker: Optional[asyncio.Task] = None

    async def start(self) -> None:
        """Initialize storage and start the background writer."""

        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self.archive_path.parent.mkdir(parents=True, exist_ok=True)
        await self._ensure_schema()
        if not self._worker or self._worker.done():
            self._worker = asyncio.create_task(self._drain_queue())

    async def stop(self) -> None:
        """Flush the queue and stop the background writer."""

        if not self._worker:
            return
        await self._queue.put(None)
        await self._worker
        self._worker = None

    async def log_execution_request(self, entry: AuditEntry) -> str:
        """Enqueue an audit entry and return its canonical reference."""

        if not self._worker or self._worker.done():
            await self.start()
        await self._queue.put(entry)
        return entry.entry_id

    async def query(self, query: AuditQuery) -> List[AuditEntry]:
        """Query audit entries with structured filters."""

        sql = [
            "SELECT entry_id, timestamp, entry_source, triggered_by, action, result, "
            "error_code, execution_status, release_ref, testplan_ref, task_ref, "
            "requirement_refs, delivery_refs, evidence_refs, client_info, metadata "
            "FROM audit_entries WHERE 1=1"
        ]
        params = []
        filters = {
            "entry_id": query.execution_id,
            "task_ref": query.task_ref,
            "testplan_ref": query.testplan_ref,
            "release_ref": query.release_ref,
            "triggered_by": query.triggered_by,
        }
        for column, value in filters.items():
            if value:
                sql.append(f"AND {column} = ?")
                params.append(value)
        if query.started_at:
            sql.append("AND timestamp >= ?")
            params.append(query.started_at)
        if query.ended_at:
            sql.append("AND timestamp <= ?")
            params.append(query.ended_at)
        sql.append("ORDER BY timestamp ASC")

        async with aiosqlite.connect(self.db_path) as conn:
            conn.row_factory = aiosqlite.Row
            async with conn.execute(" ".join(sql), params) as cursor:
                rows = await cursor.fetchall()
        return [self._row_to_entry(row) for row in rows]

    async def query_by_task(self, task_ref: str) -> List[AuditEntry]:
        return await self.query(AuditQuery(task_ref=task_ref))

    async def query_by_release(self, release_ref: str) -> List[AuditEntry]:
        return await self.query(AuditQuery(release_ref=release_ref))

    async def _ensure_schema(self) -> None:
        async with aiosqlite.connect(self.db_path) as conn:
            await conn.execute("PRAGMA journal_mode=WAL;")
            await conn.execute(
                """
                CREATE TABLE IF NOT EXISTS audit_entries (
                    entry_id TEXT PRIMARY KEY,
                    timestamp TEXT NOT NULL,
                    entry_source TEXT NOT NULL,
                    triggered_by TEXT NOT NULL,
                    action TEXT NOT NULL,
                    result TEXT NOT NULL,
                    error_code TEXT,
                    execution_status TEXT,
                    release_ref TEXT,
                    testplan_ref TEXT,
                    task_ref TEXT,
                    requirement_refs TEXT NOT NULL,
                    delivery_refs TEXT NOT NULL,
                    evidence_refs TEXT NOT NULL,
                    client_info TEXT NOT NULL,
                    metadata TEXT NOT NULL
                )
                """
            )
            await conn.commit()

    async def _drain_queue(self) -> None:
        while True:
            entry = await self._queue.get()
            if entry is None:
                self._queue.task_done()
                break
            await self._write_entry(entry)
            self._queue.task_done()

    async def _write_entry(self, entry: AuditEntry) -> None:
        payload = self._serialize_entry(entry)
        async with aiosqlite.connect(self.db_path) as conn:
            await conn.execute("PRAGMA journal_mode=WAL;")
            await conn.execute(
                """
                INSERT OR REPLACE INTO audit_entries (
                    entry_id, timestamp, entry_source, triggered_by, action, result,
                    error_code, execution_status, release_ref, testplan_ref, task_ref,
                    requirement_refs, delivery_refs, evidence_refs, client_info, metadata
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                payload,
            )
            await conn.commit()
        with self.archive_path.open("a", encoding="utf-8") as handle:
            handle.write(json.dumps(self._entry_to_dict(entry), ensure_ascii=False) + "\n")

    def _serialize_entry(self, entry: AuditEntry) -> tuple:
        return (
            entry.entry_id,
            entry.timestamp,
            entry.entry_source.value,
            entry.triggered_by,
            entry.action.value,
            entry.result,
            entry.error_code.value if entry.error_code else None,
            entry.execution_status.value if entry.execution_status else None,
            entry.path.release_ref,
            entry.path.testplan_ref,
            entry.path.task_ref,
            json.dumps(entry.axis_binding.requirement_refs, ensure_ascii=False),
            json.dumps(entry.axis_binding.delivery_refs, ensure_ascii=False),
            json.dumps(entry.axis_binding.evidence_refs, ensure_ascii=False),
            json.dumps(entry.client_info, ensure_ascii=False),
            json.dumps(entry.metadata, ensure_ascii=False),
        )

    def _entry_to_dict(self, entry: AuditEntry) -> dict:
        return {
            "entry_id": entry.entry_id,
            "timestamp": entry.timestamp,
            "entry_source": entry.entry_source.value,
            "triggered_by": entry.triggered_by,
            "action": entry.action.value,
            "result": entry.result,
            "error_code": entry.error_code.value if entry.error_code else None,
            "execution_status": entry.execution_status.value if entry.execution_status else None,
            "path": {
                "release_ref": entry.path.release_ref,
                "testplan_ref": entry.path.testplan_ref,
                "task_ref": entry.path.task_ref,
            },
            "axis_binding": {
                "requirement_refs": entry.axis_binding.requirement_refs,
                "delivery_refs": entry.axis_binding.delivery_refs,
                "evidence_refs": entry.axis_binding.evidence_refs,
            },
            "client_info": entry.client_info,
            "metadata": entry.metadata,
        }

    def _row_to_entry(self, row: aiosqlite.Row) -> AuditEntry:
        return AuditEntry(
            entry_id=row["entry_id"],
            timestamp=row["timestamp"],
            entry_source=EntrySource(row["entry_source"]),
            triggered_by=row["triggered_by"],
            action=AuditAction(row["action"]),
            result=row["result"],
            path=ExecutionPath(
                release_ref=row["release_ref"],
                testplan_ref=row["testplan_ref"],
                task_ref=row["task_ref"],
            ),
            axis_binding=SSOTAxisBinding(
                requirement_refs=json.loads(row["requirement_refs"]),
                delivery_refs=json.loads(row["delivery_refs"]),
                evidence_refs=json.loads(row["evidence_refs"]),
            ),
            error_code=QAEntryErrorCode(row["error_code"]) if row["error_code"] else None,
            execution_status=ExecutionStatus(row["execution_status"]) if row["execution_status"] else None,
            client_info=json.loads(row["client_info"]),
            metadata=json.loads(row["metadata"]),
        )
