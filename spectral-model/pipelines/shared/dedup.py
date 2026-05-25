"""Semantic deduplication using sentence-transformers and ChromaDB."""

import asyncio
import logging
import threading
from typing import Optional

from config.settings import settings

logger = logging.getLogger(__name__)


class SemanticDedup:
    """
    Async-safe semantic deduplication using sentence-transformers + ChromaDB.

    Lazy-initializes on first use to avoid slow import at startup.
    Uses a threading lock for the sentence transformer (not async-native).
    """

    def __init__(
        self,
        threshold: Optional[float] = None,
        collection_name: str = "spectral_iam_dedup",
    ):
        self.threshold = threshold or settings.dedup_threshold
        self.collection_name = collection_name
        self._model = None
        self._collection = None
        self._lock = threading.Lock()
        self._async_lock = asyncio.Lock()
        self._initialized = False

    def _ensure_initialized(self) -> None:
        """Initialize model and ChromaDB collection (thread-safe)."""
        if self._initialized:
            return

        with self._lock:
            if self._initialized:
                return

            logger.info(f"Loading sentence-transformer model: {settings.dedup_model}")
            try:
                from sentence_transformers import SentenceTransformer
                self._model = SentenceTransformer(settings.dedup_model)
            except ImportError:
                logger.warning(
                    "sentence-transformers not installed. Deduplication disabled."
                )
                self._initialized = True
                return

            logger.info(f"Initializing ChromaDB at {settings.chroma_path}")
            try:
                import chromadb
                settings.chroma_path.mkdir(parents=True, exist_ok=True)
                client = chromadb.PersistentClient(path=str(settings.chroma_path))
                self._collection = client.get_or_create_collection(
                    name=self.collection_name,
                    metadata={"hnsw:space": "cosine"},
                )
                logger.info(
                    f"ChromaDB collection '{self.collection_name}' ready. "
                    f"Items: {self._collection.count()}"
                )
            except ImportError:
                logger.warning("chromadb not installed. Deduplication disabled.")

            self._initialized = True

    def _encode(self, text: str) -> list[float]:
        """Encode text to embedding vector."""
        if self._model is None:
            return []
        embedding = self._model.encode(text, normalize_embeddings=True)
        return embedding.tolist()

    def _sync_is_duplicate(self, text: str) -> bool:
        """Synchronous duplicate check."""
        self._ensure_initialized()
        if self._collection is None or self._model is None:
            return False  # Can't check, assume not duplicate

        if self._collection.count() == 0:
            return False

        embedding = self._encode(text)
        results = self._collection.query(
            query_embeddings=[embedding],
            n_results=1,
            include=["distances"],
        )

        if results and results["distances"] and results["distances"][0]:
            # ChromaDB cosine distance: 0 = identical, 2 = opposite
            # Convert to similarity: similarity = 1 - (distance / 2)
            distance = results["distances"][0][0]
            similarity = 1.0 - (distance / 2.0)
            logger.debug(f"Nearest neighbor similarity: {similarity:.4f} (threshold: {self.threshold})")
            return similarity >= self.threshold

        return False

    def _sync_add(self, text: str, doc_id: str, metadata: Optional[dict] = None) -> None:
        """Synchronous add document to collection."""
        self._ensure_initialized()
        if self._collection is None or self._model is None:
            return

        embedding = self._encode(text)
        meta = metadata or {}
        # ChromaDB requires metadata values to be str, int, float, or bool
        clean_meta = {k: str(v) for k, v in meta.items()}

        try:
            self._collection.add(
                embeddings=[embedding],
                documents=[text[:1000]],  # Store first 1000 chars for reference
                metadatas=[clean_meta],
                ids=[doc_id],
            )
        except Exception as e:
            logger.warning(f"Failed to add to ChromaDB: {e}")

    async def is_duplicate(self, text: str) -> bool:
        """Async duplicate check. Returns True if text is too similar to existing content."""
        async with self._async_lock:
            loop = asyncio.get_event_loop()
            return await loop.run_in_executor(None, self._sync_is_duplicate, text)

    async def add(
        self,
        text: str,
        doc_id: str,
        metadata: Optional[dict] = None,
    ) -> None:
        """Async add document to deduplication store."""
        async with self._async_lock:
            loop = asyncio.get_event_loop()
            await loop.run_in_executor(None, self._sync_add, text, doc_id, metadata)

    async def check_and_add(
        self,
        text: str,
        doc_id: str,
        metadata: Optional[dict] = None,
    ) -> bool:
        """
        Check if duplicate, and if not, add to store.

        Returns:
            True if this is a duplicate (should be skipped)
            False if unique (was added to store)
        """
        async with self._async_lock:
            loop = asyncio.get_event_loop()
            is_dup = await loop.run_in_executor(None, self._sync_is_duplicate, text)
            if not is_dup:
                await loop.run_in_executor(None, self._sync_add, text, doc_id, metadata)
            return is_dup

    def count(self) -> int:
        """Return number of items in dedup store."""
        self._ensure_initialized()
        if self._collection is None:
            return 0
        return self._collection.count()
