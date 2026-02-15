"""Report upload and retrieval endpoints."""

import hashlib
from pathlib import Path

from fastapi import APIRouter, File, Form, HTTPException, UploadFile
from fastapi.responses import Response

from app.models.schemas import ReportCreate, ReportResult
from app.services.document_intelligence import (
    build_confidence_summary,
    classify_document_type,
    detect_missing_documents,
    detect_pending_forms,
    extract_structured_data,
    predict_credit_queries,
)
from app.services.pdf_generator import generate_report_pdf
from app.services.report_store import generate_report_id, get_report, save_report
from app.services.rule_engine import evaluate_eligibility

router = APIRouter(prefix="/reports", tags=["reports"])

ALLOWED_EXTENSIONS = {".pdf", ".png", ".jpg", ".jpeg", ".tiff", ".tif"}
MAX_FILE_SIZE = 10 * 1024 * 1024  # 10 MB


@router.post("/upload", response_model=ReportCreate)
async def upload_report(
    files: list[UploadFile] = File(..., description="PDF/image files"),
    user_id: str | None = Form(None),
    category: str | None = Form(None),
):
    """
    Upload one or more documents and generate consolidated eligibility report.
    """
    if not files:
        raise HTTPException(status_code=400, detail="At least one document is required")

    filenames: list[str] = []
    documents: list[dict] = []
    doc_hashes: list[str] = []
    total_size = 0
    for upload in files:
        if not upload.filename:
            raise HTTPException(status_code=400, detail="Filename is required")
        suffix = Path(upload.filename).suffix.lower()
        if suffix not in ALLOWED_EXTENSIONS:
            raise HTTPException(
                status_code=400,
                detail=f"File type not allowed. Accepted: {', '.join(sorted(ALLOWED_EXTENSIONS))}",
            )

        content = await upload.read()
        if len(content) > MAX_FILE_SIZE:
            raise HTTPException(status_code=400, detail=f"{upload.filename} exceeds 10 MB size limit")
        total_size += len(content)
        safe_name = Path(upload.filename).name
        filenames.append(safe_name)
        documents.append({"filename": safe_name, "content": content})
        doc_hashes.append(hashlib.sha256(content).hexdigest())

    extracted_data, salary_breakdown, obligations, processing = extract_structured_data(documents)
    if processing.get("low_quality"):
        raise HTTPException(status_code=422, detail="Document quality is low. Please upload a clearer scan.")

    doc_types = [classify_document_type(name) for name in filenames]
    missing_documents = detect_missing_documents(doc_types)
    pending_forms = detect_pending_forms(extracted_data, missing_documents)
    predicted_queries = predict_credit_queries(extracted_data, missing_documents, pending_forms)
    confidence_summary = build_confidence_summary(extracted_data, missing_documents)

    eligible, decisions = evaluate_eligibility(extracted_data)

    # Store report
    report_id = generate_report_id()
    metadata: dict = {}
    if user_id:
        metadata["user_id"] = user_id
    if category:
        metadata["category"] = category
    metadata["ingest"] = {
        "uploaded_files": filenames,
        "uploaded_count": len(filenames),
        "total_size_bytes": total_size,
        "sha256": doc_hashes,
    }
    metadata["processing"] = processing

    save_report(
        report_id=report_id,
        eligibility=eligible,
        decisions=decisions,
        extracted_data=extracted_data,
        salary_breakdown=salary_breakdown,
        obligations=obligations,
        missing_documents=missing_documents,
        pending_forms=pending_forms,
        predicted_queries=predicted_queries,
        confidence_summary=confidence_summary,
        metadata=metadata,
    )

    return ReportCreate(
        report_id=report_id,
        message="Report uploaded and processed successfully",
        eligibility=eligible,
    )


@router.get("/{report_id}", response_model=ReportResult)
async def get_report_result(report_id: str):
    """Retrieve eligibility result for a report."""
    report = get_report(report_id)
    if not report:
        raise HTTPException(status_code=404, detail="Report not found")

    return ReportResult(
        report_id=report["report_id"],
        created_at=report["created_at"],
        eligibility=report["eligibility"],
        decisions=report["decisions"],
        extracted_data=report["extracted_data"],
        salary_breakdown=report.get("salary_breakdown", []),
        obligations=report.get("obligations", []),
        missing_documents=report.get("missing_documents", []),
        pending_forms=report.get("pending_forms", []),
        predicted_queries=report.get("predicted_queries", []),
        confidence_summary=report.get("confidence_summary", {}),
        metadata=report["metadata"],
        pdf_available=True,
    )


@router.get("/{report_id}/pdf")
async def download_report_pdf(report_id: str):
    """Download the generated report as PDF."""
    report = get_report(report_id)
    if not report:
        raise HTTPException(status_code=404, detail="Report not found")

    pdf_bytes = generate_report_pdf(report)
    return Response(
        content=pdf_bytes,
        media_type="application/pdf",
        headers={
            "Content-Disposition": f'attachment; filename="eligibility-report-{report_id}.pdf"'
        },
    )
