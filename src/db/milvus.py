import logging

from src.config import Settings

logger = logging.getLogger(__name__)
Collection = CollectionSchema = DataType = FieldSchema = connections = utility = None


def _load_pymilvus():
    """Import pymilvus lazily so tests can import the app without Milvus runtime setup."""
    global Collection, CollectionSchema, DataType, FieldSchema, connections, utility
    if connections is not None:
        return
    from pymilvus import (
        Collection as _Collection,
        CollectionSchema as _CollectionSchema,
        DataType as _DataType,
        FieldSchema as _FieldSchema,
        connections as _connections,
        utility as _utility,
    )

    Collection = _Collection
    CollectionSchema = _CollectionSchema
    DataType = _DataType
    FieldSchema = _FieldSchema
    connections = _connections
    utility = _utility


def _escape_milvus_value(value: str) -> str:
    """Escape special characters in Milvus filter expression values."""
    return value.replace("\\", "\\\\").replace('"', '\\"')


class MilvusClient:
    def __init__(self, settings: Settings):
        self.settings = settings
        self._connect()

    def _connect(self):
        try:
            _load_pymilvus()
            connections.connect(
                alias="default",
                uri=self.settings.milvus_uri,
                user=self.settings.milvus_user or None,
                password=self.settings.milvus_password or None,
            )
            logger.info("Connected to Milvus at %s", self.settings.milvus_uri)
        except Exception:
            logger.exception("Failed to connect to Milvus at %s", self.settings.milvus_uri)
            raise

    def init_collections(self):
        self._init_knowledge_collection()
        self._init_memory_collection()

    def _init_knowledge_collection(self):
        name = self.settings.milvus_collection_know
        if utility.has_collection(name):
            self.knowledge_col = Collection(name)
            self.knowledge_col.load()
            return

        fields = [
            FieldSchema(name="id", dtype=DataType.INT64, is_primary=True, auto_id=True),
            FieldSchema(name="tenant_id", dtype=DataType.VARCHAR, max_length=64),
            FieldSchema(name="category", dtype=DataType.VARCHAR, max_length=50),
            FieldSchema(name="content", dtype=DataType.VARCHAR, max_length=5000),
            FieldSchema(name="source", dtype=DataType.VARCHAR, max_length=255),
            FieldSchema(
                name="embedding",
                dtype=DataType.FLOAT_VECTOR,
                dim=self.settings.embedding_dim,
            ),
        ]
        schema = CollectionSchema(fields, description="Jewelry knowledge base vectors")
        self.knowledge_col = Collection(name, schema)
        self.knowledge_col.create_index(
            "embedding",
            {
                "index_type": "IVF_FLAT",
                "metric_type": "COSINE",
                "params": {"nlist": 128},
            },
        )
        self.knowledge_col.load()

    def _init_memory_collection(self):
        name = self.settings.milvus_collection_memory
        if utility.has_collection(name):
            self.memory_col = Collection(name)
            self.memory_col.load()
            return

        fields = [
            FieldSchema(name="id", dtype=DataType.INT64, is_primary=True, auto_id=True),
            FieldSchema(name="tenant_id", dtype=DataType.VARCHAR, max_length=64),
            FieldSchema(name="user_id", dtype=DataType.VARCHAR, max_length=100),
            FieldSchema(name="session_id", dtype=DataType.VARCHAR, max_length=100),
            FieldSchema(name="content", dtype=DataType.VARCHAR, max_length=2000),
            FieldSchema(
                name="embedding",
                dtype=DataType.FLOAT_VECTOR,
                dim=self.settings.embedding_dim,
            ),
            FieldSchema(name="created_at", dtype=DataType.INT64),
        ]
        schema = CollectionSchema(fields, description="User chat memory vectors")
        self.memory_col = Collection(name, schema)
        self.memory_col.create_index(
            "embedding",
            {
                "index_type": "IVF_FLAT",
                "metric_type": "COSINE",
                "params": {"nlist": 128},
            },
        )
        self.memory_col.load()

    def search_knowledge(
        self, tenant_id: str, query_embedding: list[float], top_k: int = 3
    ) -> list[dict]:
        safe_tid = _escape_milvus_value(tenant_id)
        results = self.knowledge_col.search(
            data=[query_embedding],
            anns_field="embedding",
            param={"metric_type": "COSINE", "params": {"nprobe": 16}},
            limit=top_k,
            expr=f'tenant_id == "{safe_tid}"',
            output_fields=["content", "category", "source"],
        )
        hits = []
        for hit in results[0]:
            hits.append(
                {
                    "content": hit.entity.get("content"),
                    "category": hit.entity.get("category"),
                    "source": hit.entity.get("source"),
                    "score": hit.score,
                }
            )
        return hits

    def search_memory(
        self,
        tenant_id: str,
        user_id: str,
        query_embedding: list[float],
        top_k: int = 5,
    ) -> list[dict]:
        safe_tid = _escape_milvus_value(tenant_id)
        safe_uid = _escape_milvus_value(user_id)
        results = self.memory_col.search(
            data=[query_embedding],
            anns_field="embedding",
            param={"metric_type": "COSINE", "params": {"nprobe": 16}},
            limit=top_k,
            expr=f'tenant_id == "{safe_tid}" && user_id == "{safe_uid}"',
            output_fields=["content", "session_id", "created_at"],
        )
        hits = []
        for hit in results[0]:
            hits.append(
                {
                    "content": hit.entity.get("content"),
                    "session_id": hit.entity.get("session_id"),
                    "created_at": hit.entity.get("created_at"),
                    "score": hit.score,
                }
            )
        return hits

    def insert_knowledge(
        self,
        tenant_id: str,
        category: str,
        content: str,
        source: str,
        embedding: list[float],
    ):
        self.knowledge_col.insert(
            [[tenant_id], [category], [content], [source], [embedding]]
        )
        self.knowledge_col.flush()

    def batch_insert_knowledge(
        self,
        tenant_ids: list[str],
        categories: list[str],
        contents: list[str],
        sources: list[str],
        embeddings: list[list[float]],
    ):
        self.knowledge_col.insert(
            [tenant_ids, categories, contents, sources, embeddings]
        )
        self.knowledge_col.flush()

    def insert_memory(
        self,
        tenant_id: str,
        user_id: str,
        session_id: str,
        content: str,
        embedding: list[float],
        created_at: int,
    ):
        self.memory_col.insert(
            [
                [tenant_id],
                [user_id],
                [session_id],
                [content],
                [embedding],
                [created_at],
            ]
        )
        self.memory_col.flush()

    def delete_knowledge_by_doc_ids(self, tenant_id: str, doc_sources: list[str]):
        """Delete knowledge vectors by tenant_id and source filenames."""
        if not doc_sources:
            return
        safe_tid = _escape_milvus_value(tenant_id)
        sources_expr = ", ".join(f'"{_escape_milvus_value(s)}"' for s in doc_sources)
        self.knowledge_col.delete(
            f'tenant_id == "{safe_tid}" && source in [{sources_expr}]'
        )
        logger.info("Deleted %d knowledge vectors for tenant=%s", len(doc_sources), tenant_id)

    def check_health(self) -> dict:
        """Check Milvus connectivity. Returns {"status": "ok"/"error", "detail": ...}."""
        try:
            # Try a simple operation on each collection
            self.knowledge_col.num_entities
            self.memory_col.num_entities
            return {"status": "ok"}
        except Exception as e:
            return {"status": "error", "detail": str(e)}

    def close(self):
        connections.disconnect("default")
