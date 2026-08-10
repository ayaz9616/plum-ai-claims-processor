import logging

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from dataclasses import asdict
from fastapi import File, HTTPException, UploadFile
from .schemas import ClaimSubmission
from .policy import PolicyRepository
from .trace import TraceManager
from .orchestrator import ClaimOrchestrator
from .config import config
from .providers import build_provider_set
from .uploads import DocumentUploadError, DocumentUploadService

logger = logging.getLogger(__name__)

app = FastAPI(title="Plum Claims - Backend")

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000",
        "http://127.0.0.1:3000",
        "http://localhost:3001",
        "http://127.0.0.1:3001",
    ],
    allow_credentials=False,
    allow_methods=["GET", "POST", "OPTIONS"],
    allow_headers=["*"],
)

upload_service = DocumentUploadService()

@app.get("/health")
def health():
    return {"status": "ok"}


# instantiate core components for wiring tests
policy_repo = PolicyRepository(config.policy_path)
trace_manager = TraceManager()
provider_set = build_provider_set()
orchestrator = ClaimOrchestrator(policy_repo, trace_manager, provider_set)


@app.get("/api/members")
def list_members():
    """Read-only roster for the claim intake selector."""
    policy_repo.load()
    policy = policy_repo.raw() or {}
    return {"policy_id": policy.get("policy_id"), "members": [
        {"member_id": member.get("member_id"), "name": member.get("name"), "relationship": member.get("relationship")}
        for member in policy.get("members", [])
    ]}


@app.post("/api/documents/upload")
def upload_document(file: UploadFile = File(...)):
    try:
        result = upload_service.process_upload(file)
    except DocumentUploadError as exc:
        status_code = 413 if "size limit" in str(exc).lower() else 400
        raise HTTPException(status_code=status_code, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Upload failed: {exc}") from exc

    return asdict(result)


from .uploads import STAGING_DIR
from .providers import VisionRequest

@app.post("/api/documents/{document_id}/ocr")
def process_document_ocr(document_id: str):
    if not provider_set.vision:
        raise HTTPException(status_code=503, detail="Gemini Vision API is not configured.")

    staged_path = STAGING_DIR / document_id
    if not document_id or ".." in document_id or not staged_path.exists():
        raise HTTPException(status_code=404, detail="Document not found or already processed.")

    # Determine basic mime type from extension
    ext = staged_path.suffix.lower()
    mime_type = "application/octet-stream"
    if ext == ".pdf":
        mime_type = "application/pdf"
    elif ext in [".jpeg", ".jpg"]:
        mime_type = "image/jpeg"
    elif ext == ".png":
        mime_type = "image/png"
    elif ext == ".webp":
        mime_type = "image/webp"

    try:
        req = VisionRequest(
            document_path=str(staged_path),
            mime_type=mime_type
        )
        response = provider_set.vision.analyze(req)
        return {
            "status": "success",
            "document_id": document_id,
            "text": response.text,
            "metadata": response.metadata
        }
    except Exception as exc:
        # Log the real error server-side for debugging; return a safe message to the client.
        logger.exception("OCR processing failed for document %s: %s", document_id, exc)
        raise HTTPException(status_code=500, detail=f"Gemini processing failed: {type(exc).__name__}: {exc}")
    finally:
        staged_path.unlink(missing_ok=True)

@app.post("/api/claims/process")
def process_claim(submission: ClaimSubmission):
    try:
        result = orchestrator.process_claim(submission)
        # Handle both dataclasses and Pydantic models (ClaimProcessingResult is a Pydantic model)
        return asdict(result) if hasattr(result, '__dataclass_fields__') else result.model_dump(mode="python")
    except Exception as exc:
        logger.exception("Claim processing failed: %s", exc)
        raise HTTPException(status_code=500, detail=f"Processing failed: {exc}")
