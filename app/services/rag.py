import logging

from langchain_core.prompts import ChatPromptTemplate
from langchain_groq import ChatGroq

from app.core.config import Settings
from app.core.exceptions import AppError
from app.models.schemas import QueryResponse, SourceChunk
from app.services.vector_store import VectorStoreService

logger = logging.getLogger(__name__)


SYSTEM_PROMPT = """You are an enterprise financial document QA assistant.
Answer only from the retrieved context.
Be conservative: if the context does not contain enough evidence, say you do not know.
Do not invent numbers, dates, accounting conclusions, or financial facts.
Use concise prose.
For every material claim, cite the source label exactly as shown in the context, for example [quarterly.pdf#12].
If the user asks for a summary, summarize only the retrieved passages."""


class RagService:
    def __init__(self, settings: Settings, vector_store: VectorStoreService) -> None:
        self.settings = settings
        self.vector_store = vector_store
        self.prompt = ChatPromptTemplate.from_messages(
            [
                ("system", SYSTEM_PROMPT),
                ("human", "Question:\n{question}\n\nRetrieved context:\n{context}\n\nAnswer:"),
            ]
        )

    def _llm(self) -> ChatGroq:
        return ChatGroq(
            model="llama-3.3-70b-versatile",
            api_key=self.settings.groq_api_key,
            temperature=0,
        )

    def answer(self, question: str, top_k: int | None = None) -> QueryResponse:
        k = top_k or self.settings.retrieval_k

        if not self.vector_store.exists():
            return QueryResponse(
                answer="No documents have been indexed yet. Please upload a document first.",
                citations=[],
                sources=[],
            )

        retrieved = self.vector_store.search(question, k)
        if not retrieved:
            return QueryResponse(
                answer="I do not know based on the indexed documents.",
                citations=[],
                sources=[],
            )

        sources: list[SourceChunk] = []
        context_blocks: list[str] = []
        citations: list[str] = []

        seen_chunks: set[str] = set()
        for document, score in retrieved:
            normalized_text = " ".join(document.page_content.split())
            if normalized_text in seen_chunks:
                continue
            seen_chunks.add(normalized_text)
            metadata = dict(document.metadata)
            citation = f"{metadata.get('filename', 'unknown')}#{metadata.get('chunk_index', 'unknown')}"
            citations.append(citation)
            context_blocks.append(f"[{citation}]\n{document.page_content}")
            sources.append(
                SourceChunk(
                    document_id=str(metadata.get("document_id", "")),
                    filename=str(metadata.get("filename", "")),
                    chunk_id=str(metadata.get("chunk_id", "")),
                    page=metadata.get("page"),
                    row=metadata.get("row"),
                    score=float(score),
                    text=document.page_content,
                    metadata=metadata,
                )
            )

        chain = self.prompt | self._llm()
        try:
            result = chain.invoke({"question": question, "context": "\n\n".join(context_blocks)})
        except Exception as exc:
            logger.exception("Groq generation failed")
            raise AppError(
                "Failed to generate answer. Check your GROQ_API_KEY and network connection.",
                503,
            ) from exc

        answer = getattr(result, "content", str(result)).strip()
        if not answer:
            answer = self._extractive_answer(sources)
        elif answer.lower().startswith("i do not know") and sources:
            answer = self._extractive_answer(sources)
        return QueryResponse(answer=answer, citations=sorted(set(citations)), sources=sources)

    @staticmethod
    def _extractive_answer(sources: list[SourceChunk]) -> str:
        if not sources:
            return "I do not know based on the indexed documents."
        lines = ["The retrieved documents contain the following relevant evidence:"]
        for source in sources[:3]:
            citation = f"{source.filename}#{source.metadata.get('chunk_index', 'unknown')}"
            text = " ".join(source.text.split())
            excerpt = text[:500].rstrip()
            if len(text) > 500:
                excerpt = f"{excerpt}..."
            lines.append(f"- {excerpt} [{citation}]")
        return "\n".join(lines)
