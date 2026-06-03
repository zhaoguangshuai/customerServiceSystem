import logging

from fastapi import APIRouter, File, Form, HTTPException, Request, UploadFile

from src.db.mysql import KnowledgeDocument, get_session
from src.utils.document_loader import load_document, process_document

logger = logging.getLogger(__name__)

router = APIRouter()

ALLOWED_EXTENSIONS = {".pdf", ".docx", ".xlsx", ".md", ".txt"}


@router.post("/knowledge/upload")
async def upload_knowledge(
    request: Request,
    tenant_id: str = Form(...),
    category: str = Form(default="general"),
    file: UploadFile = File(...),
):
    import os

    ext = os.path.splitext(file.filename or "")[1].lower()
    if ext not in ALLOWED_EXTENSIONS:
        raise HTTPException(
            status_code=400,
            detail=f"不支持的文件类型: {ext}，仅支持: {', '.join(ALLOWED_EXTENSIONS)}",
        )

    content = await file.read()
    if len(content) > 10 * 1024 * 1024:
        raise HTTPException(status_code=400, detail="文件大小不能超过10MB")

    try:
        text = load_document(file.filename, content)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

    # Save document metadata to MySQL
    async with get_session() as session:
        doc = KnowledgeDocument(
            tenant_id=tenant_id,
            title=file.filename,
            file_type=file.filename.rsplit(".", 1)[-1] if "." in file.filename else "",
            content=text,
            category=category,
        )
        session.add(doc)
        await session.commit()

    # Vectorize and store in Milvus
    milvus = request.app.state.milvus_client
    chunk_count = await process_document(
        filename=file.filename,
        content=content,
        tenant_id=tenant_id,
        category=category,
        milvus_client=milvus,
    )

    return {
        "code": 200,
        "msg": "success",
        "data": {
            "filename": file.filename,
            "category": category,
            "chunk_count": chunk_count,
        },
    }


@router.get("/knowledge/list")
async def list_knowledge(tenant_id: str, category: str = None):
    async with get_session() as session:
        from sqlalchemy import select

        query = select(KnowledgeDocument).where(KnowledgeDocument.tenant_id == tenant_id, KnowledgeDocument.status == 1)
        if category:
            query = query.where(KnowledgeDocument.category == category)
        result = await session.execute(query)
        docs = result.scalars().all()

    return {
        "code": 200,
        "msg": "success",
        "data": [
            {
                "id": d.id,
                "title": d.title,
                "file_type": d.file_type,
                "category": d.category,
                "status": d.status,
                "created_at": d.created_at.isoformat() if d.created_at else None,
            }
            for d in docs
        ],
    }


@router.delete("/knowledge/{doc_id}")
async def delete_knowledge(doc_id: int, tenant_id: str, request: Request):
    async with get_session() as session:
        from sqlalchemy import select

        result = await session.execute(
            select(KnowledgeDocument).where(
                KnowledgeDocument.id == doc_id,
                KnowledgeDocument.tenant_id == tenant_id,
            )
        )
        doc = result.scalar_one_or_none()
        if not doc:
            raise HTTPException(status_code=404, detail="文档不存在或无权限删除")

        # Delete vectors from Milvus
        milvus = request.app.state.milvus_client
        try:
            milvus.delete_knowledge_by_doc_ids(doc.tenant_id, [doc.title])
        except Exception:
            logger.exception("Failed to delete Milvus vectors for doc_id=%d", doc_id)

        doc.status = 0
        await session.commit()

    return {"code": 200, "msg": "success"}
