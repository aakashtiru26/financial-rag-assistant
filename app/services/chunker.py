from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_core.documents import Document


class DocumentChunker:
    def __init__(self, chunk_size: int, chunk_overlap: int) -> None:
        self.splitter = RecursiveCharacterTextSplitter(
            chunk_size=chunk_size,
            chunk_overlap=chunk_overlap,
            separators=["\n\n", "\n", ". ", "; ", ", ", " ", ""],
        )

    def split(self, documents: list[Document], document_id: str, filename: str) -> list[Document]:
        chunks = self.splitter.split_documents(documents)
        for index, chunk in enumerate(chunks):
            chunk.metadata = {
                **chunk.metadata,
                "document_id": document_id,
                "filename": filename,
                "chunk_index": index,
                "chunk_id": f"{document_id}:{index}",
            }
        return chunks
