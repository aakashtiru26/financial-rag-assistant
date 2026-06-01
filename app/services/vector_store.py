import logging
from functools import lru_cache
from langchain_community.vectorstores import FAISS
from langchain_core.documents import Document
from langchain_community.embeddings import HuggingFaceEmbeddings
from app.core.config import Settings
from app.core.exceptions import AppError
from app.utils.file_utils import clear_directory

logger = logging.getLogger(__name__)

@lru_cache(maxsize=1)
def get_embedding_model():
    """Load once, reuse forever — avoids re-downloading on every request."""
    logger.info("Loading embedding model (one-time download)...")
    model = HuggingFaceEmbeddings(
        model_name="sentence-transformers/all-MiniLM-L6-v2",
        model_kwargs={"device": "cpu"},
        encode_kwargs={"normalize_embeddings": True},
    )
    logger.info("Embedding model loaded successfully.")
    return model


class VectorStoreService:
    def __init__(self, settings: Settings) -> None:
        self.settings = settings
        self.index_dir = settings.index_dir

    def exists(self) -> bool:
        return (
            (self.index_dir / "index.faiss").exists()
            and (self.index_dir / "index.pkl").exists()
        )

    def load(self) -> FAISS:
        if not self.exists():
            raise AppError("No FAISS index exists yet. Upload and index documents first.", 404)
        try:
            return FAISS.load_local(
                str(self.index_dir),
                get_embedding_model(),
                allow_dangerous_deserialization=True,
            )
        except Exception as exc:
            logger.exception("Failed to load FAISS index")
            raise AppError(f"Failed to load FAISS index: {exc}", 500) from exc

    def save_documents(self, chunks: list[Document]) -> None:
        clear_directory(self.index_dir)
        if not chunks:
            return
        try:
            ids = [str(chunk.metadata["chunk_id"]) for chunk in chunks]
            store = FAISS.from_documents(chunks, get_embedding_model(), ids=ids)
            store.save_local(str(self.index_dir))
            logger.info(f"FAISS index saved with {len(chunks)} chunks.")
        except Exception as exc:
            logger.exception("Failed to build FAISS index")
            raise AppError("Failed to build FAISS index.", 503) from exc

    def search(self, question: str, top_k: int) -> list[tuple[Document, float]]:
        store = self.load()
        try:
            return store.similarity_search_with_score(question, k=top_k)
        except Exception as exc:
            logger.exception("FAISS search failed")
            raise AppError(f"Vector search failed: {exc}", 500) from exc
