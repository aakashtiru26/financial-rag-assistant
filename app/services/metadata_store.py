import json
import logging
from pathlib import Path

from app.models.schemas import DocumentRecord

logger = logging.getLogger(__name__)


class MetadataStore:
    def __init__(self, metadata_file: Path) -> None:
        self.metadata_file = metadata_file
        self.metadata_file.parent.mkdir(parents=True, exist_ok=True)

    def list_documents(self) -> list[DocumentRecord]:
        if not self.metadata_file.exists():
            return []
        try:
            raw = json.loads(self.metadata_file.read_text(encoding="utf-8"))
            return [DocumentRecord.model_validate(item) for item in raw]
        except (json.JSONDecodeError, OSError, ValueError) as exc:
            logger.exception("Failed to load document metadata")
            raise RuntimeError(f"Document metadata is unreadable: {exc}") from exc

    def get_document(self, document_id: str) -> DocumentRecord | None:
        return next((doc for doc in self.list_documents() if doc.document_id == document_id), None)

    def upsert_document(self, record: DocumentRecord) -> None:
        documents = [doc for doc in self.list_documents() if doc.document_id != record.document_id]
        documents.append(record)
        self._write(documents)

    def delete_document(self, document_id: str) -> DocumentRecord | None:
        documents = self.list_documents()
        deleted = next((doc for doc in documents if doc.document_id == document_id), None)
        if deleted is None:
            return None
        self._write([doc for doc in documents if doc.document_id != document_id])
        return deleted

    def replace_all(self, documents: list[DocumentRecord]) -> None:
        self._write(documents)

    def _write(self, documents: list[DocumentRecord]) -> None:
        payload = [doc.model_dump(mode="json") for doc in sorted(documents, key=lambda item: item.uploaded_at)]
        self.metadata_file.write_text(json.dumps(payload, indent=2), encoding="utf-8")
