from datetime import datetime, timezone
from pathlib import Path

from fastapi import UploadFile
from langchain_core.documents import Document

from app.core.config import Settings
from app.core.exceptions import AppError
from app.models.schemas import DocumentRecord, ReindexResponse
from app.services.chunker import DocumentChunker
from app.services.document_loader import DocumentLoader
from app.services.metadata_store import MetadataStore
from app.services.vector_store import VectorStoreService
from app.utils.file_utils import remove_file, safe_filename, save_upload_file, sha256_file


class DocumentService:
    def __init__(
        self,
        settings: Settings,
        metadata_store: MetadataStore,
        loader: DocumentLoader,
        chunker: DocumentChunker,
        vector_store: VectorStoreService,
    ) -> None:
        self.settings = settings
        self.metadata_store = metadata_store
        self.loader = loader
        self.chunker = chunker
        self.vector_store = vector_store

    def list_documents(self) -> list[DocumentRecord]:
        return self.metadata_store.list_documents()

    def upload_and_index(self, upload_file: UploadFile) -> DocumentRecord:
        document_id, saved_path = save_upload_file(
            upload_file,
            self.settings.upload_dir,
            self.settings.max_upload_bytes,
        )
        filename = safe_filename(upload_file.filename or saved_path.name)
        record = DocumentRecord(
            document_id=document_id,
            filename=filename,
            content_type=upload_file.content_type,
            file_path=str(saved_path),
            file_sha256=sha256_file(saved_path),
            uploaded_at=datetime.now(timezone.utc),
            chunk_count=0,
        )

        try:
            chunks = self._chunks_for_record(record)
            record.chunk_count = len(chunks)
            self.metadata_store.upsert_document(record)
            self._rebuild_index_from_records(self.metadata_store.list_documents())
        except Exception:
            remove_file(saved_path)
            self.metadata_store.delete_document(document_id)
            raise

        return record

    def delete_document(self, document_id: str) -> DocumentRecord:
        deleted = self.metadata_store.delete_document(document_id)
        if deleted is None:
            raise AppError(f"Document '{document_id}' was not found.", 404)
        remove_file(Path(deleted.file_path))
        self._rebuild_index_from_records(self.metadata_store.list_documents())
        return deleted

    def reindex_all(self) -> ReindexResponse:
        records = self.metadata_store.list_documents()
        indexed_chunks = self._rebuild_index_from_records(records)
        return ReindexResponse(
            indexed_documents=len(records),
            indexed_chunks=indexed_chunks,
            message="Re-indexing completed.",
        )

    def _chunks_for_record(self, record: DocumentRecord) -> list[Document]:
        path = Path(record.file_path)
        if not path.exists():
            raise AppError(f"Stored file for document '{record.document_id}' is missing.", 404)
        pages = self.loader.load(path)
        return self.chunker.split(pages, record.document_id, record.filename)

    def _rebuild_index_from_records(self, records: list[DocumentRecord]) -> int:
        chunks: list[Document] = []
        refreshed_records: list[DocumentRecord] = []
        for record in records:
            record_chunks = self._chunks_for_record(record)
            refreshed_records.append(record.model_copy(update={"chunk_count": len(record_chunks)}))
            chunks.extend(record_chunks)
        self.vector_store.save_documents(chunks)
        self.metadata_store.replace_all(refreshed_records)
        return len(chunks)
