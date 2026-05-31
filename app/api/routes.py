from fastapi import APIRouter, Depends, File, UploadFile, status

from app.core.config import Settings, get_settings
from app.core.security import require_api_key
from app.models.schemas import (
    DeleteResponse,
    DocumentListResponse,
    HealthResponse,
    QueryRequest,
    QueryResponse,
    ReindexResponse,
    UploadResponse,
)
from app.services.chunker import DocumentChunker
from app.services.document_loader import DocumentLoader
from app.services.document_service import DocumentService
from app.services.metadata_store import MetadataStore
from app.services.rag import RagService
from app.services.vector_store import VectorStoreService

router = APIRouter()


def get_document_service(settings: Settings = Depends(get_settings)) -> DocumentService:
    metadata_store = MetadataStore(settings.metadata_file)
    vector_store = VectorStoreService(settings)
    return DocumentService(
        settings=settings,
        metadata_store=metadata_store,
        loader=DocumentLoader(),
        chunker=DocumentChunker(settings.chunk_size, settings.chunk_overlap),
        vector_store=vector_store,
    )


def get_rag_service(settings: Settings = Depends(get_settings)) -> RagService:
    return RagService(settings=settings, vector_store=VectorStoreService(settings))


@router.get("/health", response_model=HealthResponse)
async def health(settings: Settings = Depends(get_settings)) -> HealthResponse:
    return HealthResponse(status="ok", app_name=settings.app_name, environment=settings.environment)


@router.post(
    "/documents",
    response_model=UploadResponse,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(require_api_key)],
)
async def upload_document(
    file: UploadFile = File(...),
    document_service: DocumentService = Depends(get_document_service),
) -> UploadResponse:
    document = document_service.upload_and_index(file)
    return UploadResponse(document=document, message="Document uploaded and indexed.")


@router.get(
    "/documents",
    response_model=DocumentListResponse,
    dependencies=[Depends(require_api_key)],
)
async def list_documents(document_service: DocumentService = Depends(get_document_service)) -> DocumentListResponse:
    return DocumentListResponse(documents=document_service.list_documents())


@router.delete(
    "/documents/{document_id}",
    response_model=DeleteResponse,
    dependencies=[Depends(require_api_key)],
)
async def delete_document(
    document_id: str,
    document_service: DocumentService = Depends(get_document_service),
) -> DeleteResponse:
    document_service.delete_document(document_id)
    return DeleteResponse(
        document_id=document_id,
        deleted=True,
        message="Document deleted and index rebuilt.",
    )


@router.post(
    "/documents/reindex",
    response_model=ReindexResponse,
    dependencies=[Depends(require_api_key)],
)
async def reindex_documents(document_service: DocumentService = Depends(get_document_service)) -> ReindexResponse:
    return document_service.reindex_all()


@router.post(
    "/query",
    response_model=QueryResponse,
    dependencies=[Depends(require_api_key)],
)
async def query_documents(
    request: QueryRequest,
    rag_service: RagService = Depends(get_rag_service),
) -> QueryResponse:
    return rag_service.answer(request.question, request.top_k)
