from langchain_core.documents import Document

from app.services.chunker import DocumentChunker


def test_chunker_adds_citation_metadata() -> None:
    chunker = DocumentChunker(chunk_size=80, chunk_overlap=10)
    chunks = chunker.split(
        [Document(page_content="Revenue increased in Q1. " * 12, metadata={"page": 1})],
        document_id="doc-123",
        filename="quarterly.txt",
    )

    assert chunks
    assert chunks[0].metadata["document_id"] == "doc-123"
    assert chunks[0].metadata["filename"] == "quarterly.txt"
    assert chunks[0].metadata["chunk_id"] == "doc-123:0"
    assert chunks[0].metadata["page"] == 1
