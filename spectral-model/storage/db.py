"""Async SQLite database layer using aiosqlite."""

import json
import logging
from datetime import datetime
from pathlib import Path
from typing import Optional

import aiosqlite

from schemas.training_pair import TrainingPair
from schemas.document import SourceDocument, DocumentChunk
from schemas.problem import RealWorldProblem

logger = logging.getLogger(__name__)


CREATE_SOURCES_TABLE = """
CREATE TABLE IF NOT EXISTS sources (
    id TEXT PRIMARY KEY,
    source_type TEXT NOT NULL,
    source_id TEXT NOT NULL,
    source_url TEXT,
    title TEXT NOT NULL,
    fetched_at TEXT NOT NULL
)
"""

CREATE_DOCUMENTS_TABLE = """
CREATE TABLE IF NOT EXISTS documents (
    id TEXT PRIMARY KEY,
    source_id TEXT NOT NULL,
    content_hash TEXT NOT NULL,
    char_count INTEGER NOT NULL,
    fetched_at TEXT NOT NULL,
    FOREIGN KEY (source_id) REFERENCES sources(id)
)
"""

CREATE_CHUNKS_TABLE = """
CREATE TABLE IF NOT EXISTS chunks (
    id TEXT PRIMARY KEY,
    document_id TEXT NOT NULL,
    section_number TEXT,
    section_title TEXT,
    content TEXT NOT NULL,
    chunk_index INTEGER NOT NULL DEFAULT 0,
    FOREIGN KEY (document_id) REFERENCES documents(id)
)
"""

CREATE_PROBLEMS_TABLE = """
CREATE TABLE IF NOT EXISTS problems (
    id TEXT PRIMARY KEY,
    source_type TEXT NOT NULL,
    source_url TEXT NOT NULL,
    title TEXT NOT NULL,
    score INTEGER NOT NULL DEFAULT 0,
    tags_json TEXT NOT NULL DEFAULT '[]',
    domain TEXT,
    fetched_at TEXT NOT NULL
)
"""

CREATE_CANDIDATE_PAIRS_TABLE = """
CREATE TABLE IF NOT EXISTS candidate_pairs (
    id TEXT PRIMARY KEY,
    domain TEXT NOT NULL,
    task_type TEXT NOT NULL,
    source_type TEXT NOT NULL,
    instruction TEXT NOT NULL,
    output TEXT NOT NULL,
    quality_score REAL NOT NULL DEFAULT 0.0,
    pipeline_id TEXT NOT NULL,
    generated_at TEXT NOT NULL,
    metadata_json TEXT NOT NULL DEFAULT '{}'
)
"""

CREATE_FINAL_PAIRS_TABLE = """
CREATE TABLE IF NOT EXISTS final_pairs (
    id TEXT PRIMARY KEY,
    domain TEXT NOT NULL,
    task_type TEXT NOT NULL,
    source_type TEXT NOT NULL,
    instruction TEXT NOT NULL,
    output TEXT NOT NULL,
    quality_score REAL NOT NULL DEFAULT 0.0,
    pipeline_id TEXT NOT NULL,
    generated_at TEXT NOT NULL,
    accepted_at TEXT NOT NULL,
    metadata_json TEXT NOT NULL DEFAULT '{}'
)
"""

CREATE_PIPELINE_RUNS_TABLE = """
CREATE TABLE IF NOT EXISTS pipeline_runs (
    id TEXT PRIMARY KEY,
    pipeline_id TEXT NOT NULL,
    started_at TEXT NOT NULL,
    completed_at TEXT,
    pairs_generated INTEGER NOT NULL DEFAULT 0,
    pairs_accepted INTEGER NOT NULL DEFAULT 0,
    pairs_rejected INTEGER NOT NULL DEFAULT 0,
    error TEXT
)
"""

INDEXES = [
    "CREATE INDEX IF NOT EXISTS idx_sources_source_id ON sources(source_id)",
    "CREATE INDEX IF NOT EXISTS idx_documents_source_id ON documents(source_id)",
    "CREATE INDEX IF NOT EXISTS idx_chunks_document_id ON chunks(document_id)",
    "CREATE INDEX IF NOT EXISTS idx_candidate_pairs_domain ON candidate_pairs(domain)",
    "CREATE INDEX IF NOT EXISTS idx_candidate_pairs_pipeline ON candidate_pairs(pipeline_id)",
    "CREATE INDEX IF NOT EXISTS idx_final_pairs_domain ON final_pairs(domain)",
    "CREATE INDEX IF NOT EXISTS idx_pipeline_runs_pipeline_id ON pipeline_runs(pipeline_id)",
]


class Database:
    def __init__(self, db_path: Path):
        self.db_path = db_path
        self._conn: Optional[aiosqlite.Connection] = None

    async def initialize(self) -> None:
        """Create tables and indexes if they don't exist."""
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._conn = await aiosqlite.connect(str(self.db_path))
        self._conn.row_factory = aiosqlite.Row

        await self._conn.execute("PRAGMA journal_mode=WAL")
        await self._conn.execute("PRAGMA foreign_keys=ON")

        for stmt in [
            CREATE_SOURCES_TABLE,
            CREATE_DOCUMENTS_TABLE,
            CREATE_CHUNKS_TABLE,
            CREATE_PROBLEMS_TABLE,
            CREATE_CANDIDATE_PAIRS_TABLE,
            CREATE_FINAL_PAIRS_TABLE,
            CREATE_PIPELINE_RUNS_TABLE,
        ]:
            await self._conn.execute(stmt)

        for idx in INDEXES:
            await self._conn.execute(idx)

        await self._conn.commit()
        logger.info(f"Database initialized at {self.db_path}")

    async def close(self) -> None:
        if self._conn:
            await self._conn.close()
            self._conn = None

    async def save_document(self, doc: SourceDocument) -> None:
        """Save source document metadata (not content chunks)."""
        import hashlib
        content_hash = hashlib.sha256(doc.content.encode()).hexdigest()

        await self._conn.execute(
            """
            INSERT OR IGNORE INTO sources (id, source_type, source_id, source_url, title, fetched_at)
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            (doc.id, doc.source_type.value, doc.source_id, doc.source_url,
             doc.title, doc.fetched_at.isoformat()),
        )
        await self._conn.execute(
            """
            INSERT OR IGNORE INTO documents (id, source_id, content_hash, char_count, fetched_at)
            VALUES (?, ?, ?, ?, ?)
            """,
            (doc.id, doc.id, content_hash, len(doc.content), doc.fetched_at.isoformat()),
        )
        await self._conn.commit()

    async def save_chunk(self, chunk: DocumentChunk) -> None:
        """Save a document chunk."""
        await self._conn.execute(
            """
            INSERT OR IGNORE INTO chunks
            (id, document_id, section_number, section_title, content, chunk_index)
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            (chunk.id, chunk.document_id, chunk.section_number, chunk.section_title,
             chunk.content, chunk.chunk_index),
        )
        await self._conn.commit()

    async def save_problem(self, problem: RealWorldProblem) -> None:
        """Save a real-world problem."""
        await self._conn.execute(
            """
            INSERT OR IGNORE INTO problems
            (id, source_type, source_url, title, score, tags_json, domain, fetched_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                problem.id,
                problem.source_type.value,
                problem.source_url,
                problem.title,
                problem.score,
                json.dumps(problem.tags),
                problem.domain.value if problem.domain else None,
                problem.fetched_at.isoformat(),
            ),
        )
        await self._conn.commit()

    async def save_candidate_pair(self, pair: TrainingPair) -> None:
        """Save a candidate training pair."""
        await self._conn.execute(
            """
            INSERT OR REPLACE INTO candidate_pairs
            (id, domain, task_type, source_type, instruction, output,
             quality_score, pipeline_id, generated_at, metadata_json)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                pair.id,
                pair.domain.value,
                pair.task_type.value,
                pair.source_type.value,
                pair.instruction,
                pair.output,
                pair.quality_score,
                pair.pipeline_id,
                pair.generated_at.isoformat(),
                json.dumps({**pair.metadata, "tags": pair.tags}),
            ),
        )
        await self._conn.commit()

    async def accept_pair(self, pair: TrainingPair) -> None:
        """Move a pair from candidates to final_pairs."""
        accepted_at = datetime.utcnow().isoformat()
        await self._conn.execute(
            """
            INSERT OR REPLACE INTO final_pairs
            (id, domain, task_type, source_type, instruction, output,
             quality_score, pipeline_id, generated_at, accepted_at, metadata_json)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                pair.id,
                pair.domain.value,
                pair.task_type.value,
                pair.source_type.value,
                pair.instruction,
                pair.output,
                pair.quality_score,
                pair.pipeline_id,
                pair.generated_at.isoformat(),
                accepted_at,
                json.dumps({**pair.metadata, "tags": pair.tags}),
            ),
        )
        await self._conn.commit()

    async def start_pipeline_run(self, run_id: str, pipeline_id: str) -> None:
        """Record start of a pipeline run."""
        await self._conn.execute(
            """
            INSERT INTO pipeline_runs (id, pipeline_id, started_at)
            VALUES (?, ?, ?)
            """,
            (run_id, pipeline_id, datetime.utcnow().isoformat()),
        )
        await self._conn.commit()

    async def end_pipeline_run(
        self,
        run_id: str,
        pairs_generated: int,
        pairs_accepted: int,
        pairs_rejected: int,
        error: Optional[str] = None,
    ) -> None:
        """Record completion of a pipeline run."""
        await self._conn.execute(
            """
            UPDATE pipeline_runs
            SET completed_at = ?, pairs_generated = ?, pairs_accepted = ?,
                pairs_rejected = ?, error = ?
            WHERE id = ?
            """,
            (
                datetime.utcnow().isoformat(),
                pairs_generated,
                pairs_accepted,
                pairs_rejected,
                error,
                run_id,
            ),
        )
        await self._conn.commit()

    async def get_stats(self) -> dict:
        """Get summary statistics from the database."""
        stats = {}

        # Total pairs by domain
        cursor = await self._conn.execute(
            "SELECT domain, COUNT(*) as count FROM final_pairs GROUP BY domain ORDER BY count DESC"
        )
        rows = await cursor.fetchall()
        stats["pairs_by_domain"] = {row["domain"]: row["count"] for row in rows}

        # Total pairs by pipeline
        cursor = await self._conn.execute(
            "SELECT pipeline_id, COUNT(*) as count FROM final_pairs GROUP BY pipeline_id"
        )
        rows = await cursor.fetchall()
        stats["pairs_by_pipeline"] = {row["pipeline_id"]: row["count"] for row in rows}

        # Overall counts
        cursor = await self._conn.execute("SELECT COUNT(*) as count FROM final_pairs")
        row = await cursor.fetchone()
        stats["total_final_pairs"] = row["count"]

        cursor = await self._conn.execute("SELECT COUNT(*) as count FROM candidate_pairs")
        row = await cursor.fetchone()
        stats["total_candidate_pairs"] = row["count"]

        cursor = await self._conn.execute("SELECT COUNT(*) as count FROM sources")
        row = await cursor.fetchone()
        stats["total_sources"] = row["count"]

        # Quality score distribution
        cursor = await self._conn.execute(
            """
            SELECT
                AVG(quality_score) as avg_score,
                MIN(quality_score) as min_score,
                MAX(quality_score) as max_score
            FROM final_pairs
            """
        )
        row = await cursor.fetchone()
        stats["quality_scores"] = {
            "avg": round(row["avg_score"] or 0, 4),
            "min": round(row["min_score"] or 0, 4),
            "max": round(row["max_score"] or 0, 4),
        }

        # Recent pipeline runs
        cursor = await self._conn.execute(
            """
            SELECT pipeline_id, started_at, completed_at,
                   pairs_generated, pairs_accepted, pairs_rejected, error
            FROM pipeline_runs
            ORDER BY started_at DESC
            LIMIT 10
            """
        )
        rows = await cursor.fetchall()
        stats["recent_runs"] = [dict(row) for row in rows]

        return stats
