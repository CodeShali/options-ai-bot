"""Thin ChromaDB wrapper for vector storage and similarity search."""

import logging
from typing import Optional

from config.settings import settings
from schemas.training_pair import TrainingPair

logger = logging.getLogger(__name__)


class ChromaStore:
    """Persistent ChromaDB store for training pairs."""

    COLLECTION_NAME = "spectral_iam_pairs"

    def __init__(self):
        self._client = None
        self._collection = None
        self._model = None
        self._initialized = False

    def _ensure_initialized(self) -> None:
        if self._initialized:
            return

        try:
            import chromadb
            from sentence_transformers import SentenceTransformer

            settings.chroma_path.mkdir(parents=True, exist_ok=True)
            self._client = chromadb.PersistentClient(path=str(settings.chroma_path))
            self._collection = self._client.get_or_create_collection(
                name=self.COLLECTION_NAME,
                metadata={"hnsw:space": "cosine"},
            )
            self._model = SentenceTransformer(settings.dedup_model)
            logger.info(
                f"ChromaStore initialized with {self._collection.count()} existing pairs"
            )
        except ImportError as e:
            logger.warning(f"ChromaStore initialization failed (missing dependency): {e}")

        self._initialized = True

    def _encode(self, text: str) -> list[float]:
        if self._model is None:
            return []
        embedding = self._model.encode(text[:512], normalize_embeddings=True)
        return embedding.tolist()

    def add_pair(self, pair: TrainingPair) -> None:
        """Add a training pair to the vector store."""
        self._ensure_initialized()
        if self._collection is None:
            return

        text = f"{pair.instruction} {pair.output[:500]}"
        embedding = self._encode(text)
        if not embedding:
            return

        metadata = {
            "domain": pair.domain.value,
            "task_type": pair.task_type.value,
            "source_type": pair.source_type.value,
            "quality_score": str(pair.quality_score),
            "pipeline_id": pair.pipeline_id,
        }

        try:
            self._collection.add(
                embeddings=[embedding],
                documents=[text[:1000]],
                metadatas=[metadata],
                ids=[pair.id],
            )
        except Exception as e:
            logger.warning(f"Failed to add pair {pair.id} to ChromaStore: {e}")

    def is_duplicate(self, text: str, threshold: Optional[float] = None) -> bool:
        """Check if text is semantically similar to existing pairs."""
        self._ensure_initialized()
        if self._collection is None:
            return False

        if self._collection.count() == 0:
            return False

        threshold = threshold or settings.dedup_threshold
        embedding = self._encode(text)
        if not embedding:
            return False

        try:
            results = self._collection.query(
                query_embeddings=[embedding],
                n_results=1,
                include=["distances"],
            )
            if results and results["distances"] and results["distances"][0]:
                distance = results["distances"][0][0]
                similarity = 1.0 - (distance / 2.0)
                return similarity >= threshold
        except Exception as e:
            logger.warning(f"ChromaStore query failed: {e}")

        return False

    def count(self) -> int:
        """Return number of items in the store."""
        self._ensure_initialized()
        if self._collection is None:
            return 0
        return self._collection.count()

    def search_similar(
        self,
        text: str,
        n_results: int = 5,
        domain_filter: Optional[str] = None,
    ) -> list[dict]:
        """Find similar pairs to a query text."""
        self._ensure_initialized()
        if self._collection is None or self._collection.count() == 0:
            return []

        embedding = self._encode(text)
        if not embedding:
            return []

        where = {"domain": domain_filter} if domain_filter else None
        kwargs = {
            "query_embeddings": [embedding],
            "n_results": min(n_results, self._collection.count()),
            "include": ["documents", "metadatas", "distances"],
        }
        if where:
            kwargs["where"] = where

        try:
            results = self._collection.query(**kwargs)
            items = []
            for i, doc in enumerate(results.get("documents", [[]])[0]):
                meta = results.get("metadatas", [[]])[0][i] if results.get("metadatas") else {}
                distance = results.get("distances", [[]])[0][i] if results.get("distances") else 0
                items.append({
                    "text": doc,
                    "metadata": meta,
                    "similarity": 1.0 - (distance / 2.0),
                })
            return items
        except Exception as e:
            logger.warning(f"ChromaStore search failed: {e}")
            return []
