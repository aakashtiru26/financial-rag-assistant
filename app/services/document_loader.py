from pathlib import Path

from langchain_community.document_loaders import CSVLoader, Docx2txtLoader, PyPDFLoader, TextLoader
from langchain_core.documents import Document

from app.core.exceptions import AppError


class DocumentLoader:
    def load(self, path: Path) -> list[Document]:
        extension = path.suffix.lower()
        try:
            if extension == ".pdf":
                return PyPDFLoader(str(path)).load()
            if extension == ".docx":
                return Docx2txtLoader(str(path)).load()
            if extension == ".txt":
                return TextLoader(str(path), encoding="utf-8", autodetect_encoding=True).load()
            if extension == ".csv":
                return CSVLoader(str(path), encoding="utf-8").load()
        except Exception as exc:
            raise AppError(f"Failed to parse document '{path.name}': {exc}", 422) from exc
        raise AppError(f"Unsupported document type: {extension}", 415)
